# check environment
import logging
import commands
import re
import os
import math
import glob
import yaml
from eayunstack_tools.doctor import common
from eayunstack_tools.utils import register_decorater, userful_msg, get_node_list, ssh_connect2
from eayunstack_tools.logger import fmt_print, valid_print
from utils import check_service
from eayunstack_tools.utils import NODE_ROLE
from eayunstack_tools.logger import fmt_print
from eayunstack_tools.utils import ping

from eayunstack_tools.logger import StackLOG as LOG
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
        for role in ['controller','compute','mongo','ceph-osd']:
            node_list = get_node_list(role)
            for node in node_list:
                LOG.info('%s Role: %-10s Node: %-13s %s' % ('*'*15, role, node, '*'*15))
                out, err = ssh_connect2(node, 'sudo eayunstack doctor env -a')
                if err:
                    LOG.error('Check failed !')
    else:
        for i in register.all:
            eval(i)()


@userful_msg()
@register
def check_ntp():
    check_service('ntpd')
    (s, out) = commands.getstatusoutput(
        'ntpstat | grep "synchronised to NTP server"')
    if s != 0:
        LOG.error('ntpstat error, please check it')
        return
    else:
        p = re.compile(r'.+\((.+)\).+')
        try:
            server = p.match(out).groups()[0]
            LOG.info('ntpserver is %s' % server)
        except:
            LOG.error('except ntpstate error, please check it')
            return


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
            fmt_print('SELinux current state is: %s' % current_state)
        else:
            LOG.warn('SELinux current state is: %s' % current_state)
            LOG.error('SELinux state need to be %s ' %
                      correct_state.capitalize())

    # check profile /etc/sysconfig/selinux
    current_conf = commands.getoutput(
        'grep "^SELINUX=" /etc/sysconfig/selinux | cut -d "=" -f 2')
    if current_conf == correct_conf:
        fmt_print('SELinux current conf in profile is: %s' % current_conf)
    else:
        LOG.warn('SELinux current conf in profile is: %s' % current_conf)
        LOG.error('SELinux configuration in profile need to be %s '
                  % correct_conf)


@userful_msg()
@register
def check_disk():
    limit = 85
    vfs = os.statvfs("/")
    # get "/" filesystem space used percent
    used_percent = int(math.ceil((
        float(vfs.f_blocks-vfs.f_bavail)/float(vfs.f_blocks))*100))
    if used_percent >= 0 and used_percent < limit:
        fmt_print('The "/" filesystem used %s%% space !' % used_percent)
    elif used_percent >= limit:
        LOG.warn('The "/" filesystem used %s%% space !' % used_percent)


def _network_get_nic_status():
    tmp = glob.glob('/sys/class/net/*/device')
    nics = dict()
    warn = False
    for i in tmp:
        name = i.split('/')[4]
        (status, out) = commands.getstatusoutput(
            "ethtool %s | \grep 'Link detected:'" % (name))
        if 'yes' in out:
            status = 'yes'
        else:
            status = 'no'
            warn = True
        nics[name] = status
    return nics


def _network_local_network_inf(cfg):
    network_scheme = cfg['network_scheme']

    def _find_phy_port(role):
        port = None
        try:
            action = filter(lambda scheme: scheme['action'] == 'add-patch'
                            and role in scheme['bridges'],
                            network_scheme['transformations'])[0]
            br_phy = (set(action['bridges']) - set([role])).pop()
            action = filter(lambda scheme: scheme['action'] == 'add-port'
                            and br_phy == scheme['bridge'],
                            network_scheme['transformations'])[0]
            port = action['name']
        except:
            port = None
            #LOG.error('failed to find physics nic for role:%s' % role)
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
    nic_need = [i['phy_port'] for i in local_inf]
    for nic in nic_need:
        if nic_status[nic].lower() != 'yes':
            LOG.error('Network card %s is not connected' % nic)
        else:
            LOG.debug('Network card %s connected' % nic)


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
            node_inf['storage_address'] = n['storage_address']
            all_node_inf.append(node_inf)
        except:
            #LOG.error("failed to parse node:%s" % n['fqdn'])
            continue
    return all_node_inf


def _network_check_remote(remote_inf):
    for inf in remote_inf:
        LOG.debug('=====> start ping openstack admin addr of %s(%s):' %
                  (inf['host'], inf['role']))
        ping(inf['internal_address'])
        LOG.debug('=====> start ping storage addr of %s(%s):' %
                  (inf['host'], inf['role']))
        ping(inf['storage_address'])
        if NODE_ROLE.is_controller() and inf['role'] == 'controller':
            LOG.debug('=====> start ping public addr of %s(%s):' %
                      (inf['host'], inf['role']))
            ping(inf['public_address'])


@userful_msg()
@register
def check_network():
    nic_status = _network_get_nic_status()
    cfg = yaml.load(file('/etc/astute.yaml'))

    # check node's nic status
    local_inf = _network_local_network_inf(cfg)
    _network_check_local(local_inf, nic_status)

    # check if node can connect to other node
    remote_inf = _network_remote_network_inf(cfg)
    _network_check_remote(remote_inf)


def check_nodes(obj_name):
   # node_list = get_node_list('all')
    for role in ['controller','compute','mongo','ceph-osd']:
        node_list = get_node_list(role)
        for node in node_list:
            LOG.info('%s Role: %-10s Node: %-13s %s' % ('*'*15, role, node, '*'*15))
            out, err = ssh_connect2(node, 'sudo eayunstack doctor env -n %s' % obj_name)
            if err:
                LOG.error('Check failed !')
