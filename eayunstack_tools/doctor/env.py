# check environment
import commands
import re
import os
import math
import glob
import yaml
from eayunstack_tools.doctor import common
from eayunstack_tools.utils import get_node_list
from eayunstack_tools.doctor.utils import register_decorater, userful_msg
from eayunstack_tools.doctor.utils import run_doctor_on_nodes
from eayunstack_tools.doctor.utils import get_cpu_processors, get_cpu_load
from eayunstack_tools.doctor.utils import search_service
from eayunstack_tools.sys_utils import ssh_connect2, ping
from utils import check_service
from eayunstack_tools.utils import NODE_ROLE

from eayunstack_tools.logger import StackLOG as LOG
from collections import OrderedDict
from decimal import Decimal
from pymongo import MongoClient

register = register_decorater()


def env(parser):
    if NODE_ROLE.is_unknown():
        LOG.error('Can not confirm the node role!')
        return
    if parser.CHECK_ALL:
        if not parser.OBJECT_NAME:
            check_all()
        else:
            check_nodes(parser.OBJECT_NAME)
    elif parser.OBJECT_NAME:
        object_func = 'check_%s' % (parser.OBJECT_NAME)
        eval(object_func)()
    else:
        # TODO: print usage
        pass


def make(parser):
    '''Check Environment Object'''
    # choices is something like ['ntp', 'selinux', 'disk', 'network'],
    # which depends on the functions you define below
    parser.add_argument(
        '-n',
        dest='OBJECT_NAME',
        choices=[i.split('_')[1] for i in register.all],
        help='Object Name',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=env)


def check_all():
    '''Check All Environement Object'''
    if NODE_ROLE.is_fuel():
        check_cmd = get_check_cmd('all')
        nodes = []
        for role in ['controller','compute','mongo','ceph-osd']:
            node_list = get_node_list(role)
            for node in node_list:
                node_info = {}
                node_info['role'] = role
                node_info['name'] = node
                nodes.append(node_info)
        result = run_doctor_on_nodes(nodes, check_cmd)
        for res in result:
            LOG.info(res, remote=True)
    else:
        for i in register.all:
            eval(i)()

def _get_ntpserver():
    (s, o) = commands.getstatusoutput(
        'ntpq -pn 2> /dev/null | egrep \'^\*|^\+\' | awk \'{print $1}\'')
    if s != 0 or not o:
        return
    ntpservers = sorted(o.split('\n'))
    ntpserver = ntpservers[0][1:]
    return ntpserver

@userful_msg()
@register
def check_ntp():
    check_service('ntpd')
    ntpserver = _get_ntpserver()
    if not ntpserver:
        LOG.error('Can not get ntp server, please check it.')
    else:
        LOG.debug('ntpserver is %s' % ntpserver)

def _get_mongodb_stats(yaml_path):
    configs = yaml.load(file(yaml_path))
    mongodb_pw = configs['ceilometer']['db_password']
    mongodb_url = 'mongodb://ceilometer:%s@127.0.0.1:27017/ceilometer' \
                  % mongodb_pw
    try:
	client = MongoClient(mongodb_url)
        db = client.ceilometer
        result = db.command("dbstats")
    except Exception,e:
        result = e
    return result

@userful_msg()
@register
def check_mongodb():
    if NODE_ROLE.is_mongo():
       role = NODE_ROLE.role
       if  search_service('mongod'):
           LOG.error('mongod service was not found on %s node,please fix it' \
	             % role )
       else:
           yaml_path = '/etc/astute.yaml'
           check_service('mongod')
           mongodb_stats = _get_mongodb_stats(yaml_path)            
           if isinstance(mongodb_stats,dict):
                LOG.debug("mongod service is ok:%s" % mongodb_stats)
           else:
                LOG.error('mongod service is wrong:%s' % mongodb_stats)     

def _log_time(log_path,start_time):
    with open(log_path,'w') as f:
        f.write(start_time)

def _get_from_ps():
    start_time = None
    (status,info) = commands.getstatusoutput('sudo service rabbitmq-server \
                                             status')
    if status == 0:
        pid = re.search('(?<={pid,)\d+(?=})',info).group(0)
	start_time = commands.getoutput('ps -p %s -o lstart | grep -v \
	                                "START"' % pid )
    return start_time

def _get_from_log(log_path):
    with open(log_path) as f:
        log_start_time = f.read().strip()
    return log_start_time

@userful_msg()
@register
def check_rabbitmqrestart():
    if NODE_ROLE.is_controller():
        log_path = '/.eayunstack/rabbitmq_start_time'
        start_time = _get_from_ps()
        if os.path.exists(log_path):
            log_start_time = _get_from_log(log_path)
	    if log_start_time == start_time:
	        LOG.debug('service rabbitmq has never been restart')
	    else:
	        LOG.warn('service rabbitmq has been restart at %s' % start_time)
	        _log_time(log_path,start_time)
        else:
            LOG.debug('the log file is not found')
	    _log_time(log_path,start_time)

@userful_msg()
@register
def check_selinux():
    # Correct state [enforcing, permissive, disabled]
    correct_state = correct_conf = "disabled"

    # check current state
    (s, out) = commands.getstatusoutput('getenforce')
    current_state = out
    if s != 0:
        LOG.error('getenforce error, please check it')
    else:
        if current_state == correct_state.capitalize():
            LOG.debug('SELinux current state is: %s' % current_state)
        else:
            LOG.warn('SELinux current state is: %s' % current_state)
            LOG.error('SELinux state need to be %s ' %
                      correct_state.capitalize())

    # check profile /etc/sysconfig/selinux
    current_conf = commands.getoutput(
        'grep "^SELINUX=" /etc/sysconfig/selinux | cut -d "=" -f 2')
    if current_conf == correct_conf:
        LOG.debug('SELinux current conf in profile is: %s' % current_conf)
    else:
        LOG.warn('SELinux current conf in profile is: %s' % current_conf)
        LOG.error('SELinux configuration in profile need to be %s '
                  % correct_conf)

@userful_msg()
@register
def check_daemon():
    error_memory = 50.0
    warn_memory = 30.0
    (status,info) = commands.getstatusoutput('ps aux|sort -rn -k4|head -3')
    if status == 0:
        daemons = info.split("\n")
        for daemon in daemons[:3]:
            message = ' '.join(filter(lambda x: x, daemon.split(' ')))
            pid = message.split(' ')[1]
            max_memory = float(message.split(' ')[3])
            if max_memory > warn_memory:
                if max_memory <= error_memory:
                    warn_info = ('the memory of %s(pid) usage %.1f%% '
                                 'more than %.1f%% and less than %.1f%%!'
                                 % (pid,
                                    max_memory,
                                    warn_memory,
                                    error_memory))
                    LOG.warn(warn_info)
                else:
                    error_info = ('the memory of %s(pid) usage %.1f%% '
                                  'more than %.1f%%!'
                                  % (pid, max_memory, error_memory))
                    LOG.error(error_info)
            else:
                LOG.debug('the memory of %s(pid) usage %.1f%%'
                          % (pid, max_memory))

@userful_msg()
@register
def check_disk():
    limit = 85
    vfs = os.statvfs("/")
    # get "/" filesystem space used percent
    used_percent = int(math.ceil((
        float(vfs.f_blocks-vfs.f_bavail)/float(vfs.f_blocks))*100))
    if used_percent >= 0 and used_percent < limit:
        LOG.debug('The "/" filesystem used %s%% space !' % used_percent)
    elif used_percent >= limit:
        LOG.warn('The "/" filesystem used %s%% space !' % used_percent)

#Check Memory Use /proc/meminfo file
@userful_msg()
@register
def check_memory():
    ''' Return the information in /proc/meminfo
    as a dictionary '''
    limit = 85
    meminfo=OrderedDict()

    with open('/proc/meminfo') as f:
        for line in f:
            meminfo[line.split(':')[0]] = line.split(':')[1].strip()

    Total = int((meminfo['MemTotal']).strip('kB')) / 1024.0
    UseMemory = Total - (int((meminfo['MemFree']).strip('kB'))) / 1024.0 -(int((meminfo['Buffers']).strip('kB')))/1024.0 -(int((meminfo['Cached']).strip('kB'))) /1024.0

    mem_per = UseMemory / Total * 100
    if mem_per >= 0 and mem_per < limit:
        LOG.debug('The system memory has been used %.2f%%!' % mem_per)
    elif mem_per >= limit:
        LOG.error('The system memory has been used %.2f%%!' % mem_per)


def _network_get_nic_status():
    tmp = glob.glob('/sys/class/net/*/device')
    nics = dict()
    for i in tmp:
        name = i.split('/')[4]
        (status, out) = commands.getstatusoutput(
            "ethtool %s | \grep 'Link detected:'" % (name))
        if 'yes' in out:
            status = 'yes'
        else:
            status = 'no'
        nics[name] = status
    return nics


def _network_local_network_inf(cfg):
    network_scheme = cfg['network_scheme']

    def _find_phy_port(role):
        port = []
        action = filter(lambda scheme: scheme['action'] == 'add-patch'
                        and role in scheme['bridges'],
                        network_scheme['transformations'])[0]
        br_phy = (set(action['bridges']) - set([role])).pop()
        port_actions = filter(lambda scheme: scheme['action'] == 'add-port'
                             and br_phy == scheme['bridge'],
                             network_scheme['transformations'])
        bond_actions = filter(lambda scheme: scheme['action'] == 'add-bond'
                             and br_phy == scheme['bridge'],
                             network_scheme['transformations'])
        if port_actions:
            action = port_actions[0]
            port.append(action['name'])
        elif bond_actions:
            action = bond_actions[0]
            port.extend(action['interfaces'])
        else:
            port = []
            LOG.error('failed to find physics nic for role:%s' % role)
        return port

    def _find_role_ip(role):
        try:
            # IP address here is something
            # like: {'IP': ['172.16.200.7/24'], 'other_nets': []}
            # we need to hack it
            return network_scheme['endpoints'][role]['IP'][0].split('/')[0]
        except:
            return None

    def _find_role_gw(role):
        try:
            return network_scheme['endpoints'][role]['gateway']
        except:
            return None

    network_roles = network_scheme['roles'].values()
    net_inf = []
    for r in network_roles:
        port = _find_phy_port(r)
        ip = _find_role_ip(r)
        gateway = _find_role_gw(r)
        net_inf.append({'name': r, 'phy_port': port,
                        'ip': ip, 'gateway': gateway})
    return net_inf


def _network_check_local(local_inf, nic_status):
    # 1) check if nic we need link is ok
    if NODE_ROLE.is_mongo():
        local_inf = [i for i in local_inf if i['name']
                     not in ['br-storage', 'br-prv']]
    if NODE_ROLE.is_ceph_osd():
        local_inf = [i for i in local_inf if i['name'] != 'br-prv']

    nic_need = []
    for inf in local_inf:
        nic_need.extend(inf['phy_port'])
    for nic in set(nic_need):
        # if two network roles use same nic, e.g. br-mgmt and br-fw-admin
        # use eno1, we can ignore it since we just want physic network nic
        inf = filter(lambda inf: nic in inf['phy_port'], local_inf)[0]
        if nic_status[nic].lower() != 'yes':
            LOG.error('Network card %s(%s) is not connected' %
                      (nic, inf['name']))
        else:
            LOG.debug('Network card %s(%s) connected' %
                      (nic, inf['name']))


def _network_remote_network_inf(cfg):
    nodes = cfg['nodes']
    all_node_inf = []
    for n in nodes:
        try:
            node_inf = {}
            if n['role'].endswith('controller'):
                # dont care primary-controller, consider it as normal
                # controller
                node_inf['role'] = 'controller'
            else:
                node_inf['role'] = n['role']
            if n['role'].endswith('controller'):
                node_inf['public_address'] = n['public_address']
            node_inf['internal_address'] = n['internal_address']
            node_inf['host'] = n['fqdn']
            if not n['role'].endswith('mongo'):
                node_inf['storage_address'] = n['storage_address']
            if n['role'].endswith('ceph-osd'):
                node_inf['ceph_cluster_address'] = n['ceph_cluster_address']
            all_node_inf.append(node_inf)
        except:
            LOG.error("failed to parse node:%s" % n['fqdn'])
            continue
    return all_node_inf


def _network_check_remote(remote_inf):
    def _ping(peer_inf, role):
        LOG.debug('=====> start ping %s of %s(%s):' %
                  (role, peer_inf['host'], peer_inf['role']))
        network_role = role.split('_')[0]
	hostname = peer_inf['host'].split(".")[0]
        ping(peer_inf[role],hostname,network_role)

    for inf in remote_inf:
        _ping(inf, 'internal_address')
        if (not NODE_ROLE.is_mongo()) and (not inf['role'].endswith('mongo')):
            _ping(inf, 'storage_address')
        if NODE_ROLE.is_controller() and inf['role'] == 'controller':
            _ping(inf, 'public_address')
        if NODE_ROLE.is_ceph_osd() and inf['role'] == 'ceph-osd':
            _ping(inf, 'ceph_cluster_address')


@userful_msg()
@register
def check_network():
    nic_status = _network_get_nic_status()
    if NODE_ROLE.is_fuel():
        LOG.debug('Network card information:')
        for i in nic_status.keys():
            LOG.debug('%s: %s' % (i, nic_status[i]))
        return
    cfg = yaml.load(file('/etc/astute.yaml'))

    # check node's nic status
    local_inf = _network_local_network_inf(cfg)
    _network_check_local(local_inf, nic_status)

    # check if node can connect to other node
    remote_inf = _network_remote_network_inf(cfg)
    _network_check_remote(remote_inf)

@userful_msg()
@register
def check_cpu():
    if not intel_pstate_enabled():
        LOG.debug('kernel parameter "intel_pstate" was disabled.')
        return
    (status, out) = commands.getstatusoutput(
        "cpupower frequency-info | grep \"current policy\" | awk \'{print $7}\'")
    if status != 0:
        LOG.error('Can not get CPU min frequency !')
        return
    else:
        cpu_min_freq = out
        (status, out) = commands.getstatusoutput(
            "cpupower frequency-info | grep \"current policy\" | awk \'{print $8}\'")
        cpu_min_freq_unit = out
    (status, out) = commands.getstatusoutput(
        "cpupower frequency-info | grep \"current policy\" | awk \'{print $10}\'")
    if status != 0:
        LOG.error('Can not get CPU max frequency !')
        return
    else:
        cpu_max_freq = out
        (status, out) = commands.getstatusoutput(
            "cpupower frequency-info | grep \"current policy\" | awk \'{print $11}\'")
        cpu_max_freq_unit = out
    (status, out) = commands.getstatusoutput(
        "cpupower frequency-info | grep \"current CPU frequency\" | awk \'{print $5}\'")
    if status != 0:
        LOG.error('Can not get current CPU frequency !')
        return
    else:
        cpu_cur_freq = out
        (status, out) = commands.getstatusoutput(
            "cpupower frequency-info | grep \"current CPU frequency\" | awk \'{print $6}\'")
        cpu_cur_freq_unit = out
    if float(cpu_cur_freq) >= float(cpu_min_freq) and float(cpu_cur_freq) <= float(cpu_max_freq):
        LOG.debug('Current CPU Frequency: %s %s' % (cpu_cur_freq, cpu_cur_freq_unit))
    else:
        LOG.error('Current CPU Frequency: %s %s. Not within %s %s and %s %s' % (cpu_cur_freq, cpu_cur_freq_unit, cpu_min_freq, cpu_min_freq_unit, cpu_max_freq, cpu_max_freq_unit))

def intel_pstate_enabled():
    (status, out) = commands.getstatusoutput(
        "lsmod | grep -q \"^acpi_cpufreq\"")
    if status == 0:
        return True
    else:
        return False

def check_nodes(obj_name):
   # node_list = get_node_list('all')
    check_cmd = get_check_cmd(obj_name)
    nodes = []
    for role in ['controller','compute','mongo','ceph-osd']:
        node_list = get_node_list(role)
        for node in node_list:
            node_info = {}
            node_info['role'] = role
            node_info['name'] = node
            nodes.append(node_info)
    result = run_doctor_on_nodes(nodes, check_cmd)
    for res in result:
        LOG.info(res, remote=True)

def get_check_cmd(obj_name):
    main_cmd = 'sudo eayunstack'
    sub_cmd = ' doctor env'
    if obj_name == 'all':
        cmd_args = ' -a'
    else:
        cmd_args = ' -n ' + obj_name
    if LOG.enable_debug:
        check_cmd = main_cmd + ' --debug' + sub_cmd + cmd_args
    else:
        check_cmd = main_cmd + sub_cmd + cmd_args
    return check_cmd

@userful_msg()
@register
def check_cpuload():
    cpu_processors = get_cpu_processors()
    if not cpu_processors:
        LOG.error('Can not get cpu cores!')
        return
    # get cpu load limit
    cpu_load_warn_limit = cpu_processors * 0.7
    cpu_load_error_limit = cpu_processors * 0.9
    # get cpu load averages(one, five, and fifteen minute averages)
    cpu_load = get_cpu_load()
    if not cpu_load:
        LOG.error('Can not get cpu load!')
        return
    # use five minute average to confirm the cpu load status
    cpu_load_five_minute_average = cpu_load.split(',')[1].strip()
    if Decimal(cpu_load_five_minute_average) > Decimal(cpu_load_error_limit):
        LOG.error('Current CPU load averages is : %s. '
                  'Please check system status.' % cpu_load)
    elif Decimal(cpu_load_five_minute_average) > Decimal(cpu_load_warn_limit):
        LOG.warn('Current CPU load averages is : %s. '
                 'Please check system status.' % cpu_load)
    else:
        LOG.debug('Current CPU load averages is : %s.' % cpu_load)
