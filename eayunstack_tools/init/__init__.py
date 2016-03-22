import sys
import logging
import os
import yaml
from fuelclient.client import APIClient
from eayunstack_tools.sys_utils import scp_connect
from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.utils import NODE_ROLE
from eayunstack_tools.sys_utils import ssh_connect, run_cmd_on_nodes
from eayunstack_tools.utils import get_node_list
from eayunstack_tools.sys_utils import run_command


def make(parser):
    '''EayunStack Environment Initialization'''
    parser.add_argument(
        '-u', '--update',
        action='store_true',
        dest='UPDATE',
        default=False,
        help='Update this tool on all nodes',
    )
    parser.set_defaults(func=init)


def init(parser):
    if NODE_ROLE.is_unknown():
        LOG.error('Can not confirm the node role!')
    if not NODE_ROLE.is_fuel():
        LOG.warn('This command can only run on fuel node !')
        return
    if parser.UPDATE:
        update()
        return
    init_env()
    init_node_list_file()
    init_node_role_file()

def init_node_list_file():
    # generate node-list file
    LOG.info('Generate node-list file ...')
    file_path = '/.eayunstack/node-list'
    if not os.path.exists(os.path.dirname(file_path)):
        os.mkdir(os.path.dirname(file_path))
    if os.path.exists(file_path):
        os.remove(file_path)
    logging.disable(logging.CRITICAL)
    rep = APIClient.get_request("nodes/")
    logging.disable(logging.NOTSET)
    ips = []
    for node in rep:
        fqdn = node['fqdn']
        ip = node['ip']
        ips.append(ip)
        roles = ''
        if len(node['roles']) > 1:
            for n in node['roles']: 
                if not roles:
                    roles = roles + n
                else:
                    roles = roles + ',' + n
        else:
            roles = node['roles'][0]
        host = fqdn.split('.')[0]
        mac = node['mac'].replace(':', '.')
        idrac_addr = get_idrac_addr(ip)
        entry = fqdn + ':' + host + ':' + ip + ':' + roles + ':' + mac + ':' + idrac_addr + '\n'
        output = open(file_path,'a')
        output.write(entry)
        output.close()
    # scp node-list file to all nodes
    LOG.info('Copy node-list file to all nodes ...')
    for ip in ips:
        LOG.info('   To node %s ...' % ip)
        scp_connect(ip, file_path, file_path)

def init_node_role_file():
    file_path = '/.eayunstack/node-role'
    tmp_path = ('/tmp/node-role')
    # init local node-role file
    LOG.info('Generate node-role file for fuel node ...')
    output = open(file_path,'w')
    output.write('fuel\n')
    output.close()
    # init openstack node node-role file
    LOG.info('Generate node-role file for openstack node ...')
    logging.disable(logging.CRITICAL)
    rep = APIClient.get_request("nodes/")
    logging.disable(logging.NOTSET)
    for node in rep:
        ip = node['ip']
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        output = open(tmp_path,'a')
        for role in node['roles']:
            output.write(role + '\n')
        output.close()
        LOG.info('   To node %s ...' % ip)
        scp_connect(ip, tmp_path, file_path) 

def get_idrac_addr(node_ip):
    cmd_get_idrac_addr = 'ipmitool lan print | grep -v  "IP Address Source" | grep "IP Address"'
    (out, err) = ssh_connect(node_ip, cmd_get_idrac_addr)
    if out:
        # return idrac address
        return out.split(":")[1].strip()
    else:
        return ''

def update():
    '''update eayunstack-tools on all nodes'''
    node_list = get_node_list('all')
    update_cmd = 'yum clean all && yum -y -d 0 update eayunstack-tools'
    results = run_cmd_on_nodes(node_list, update_cmd)
    get_current_version = \
        'rpm --queryformat "%{VERSION} %{RELEASE}" -q eayunstack-tools'
    current_version = run_cmd_on_nodes(node_list, get_current_version)
    correct_version = run_command(
        'rpm --queryformat "%{VERSION} %{RELEASE}" -q eayunstack-tools')

    for node in node_list:
        out = results[node][0]
        err = results[node][1]
        current_ver = current_version[node][0].split(' ')[0] + \
            '-' + current_version[node][0].split(' ')[1].split('.')[0]
        correct_ver = correct_version[0].split(' ')[0] + \
            '-' + correct_version[0].split(' ')[1].split('.')[0]
        if err or current_ver != correct_ver:
            LOG.error('Update on %s failed !' % node)
            LOG.error('Current version: %s' % current_ver)
            for l in err.split('\n'):
                LOG.error(l)
            print
        else:
            LOG.info('Update on %s successfully.' % node)
            LOG.info('Current version: %s' % current_ver)
            print

def init_env():
    env_file = '/.eayunstack/.env.yaml'
    if not os.path.exists(env_file):
        os.mknod(env_file)
    f = open(env_file)
    env_info = yaml.load(f)
    f.close()
    if not env_info:
        env_info = {}
    if env_info.has_key('env_name'):
        env_name = env_info['env_name']
    else:
        env_name = ''
    env_name = raw_input('Please enter environment name [%s]: '
                         % env_name)
    if env_name:
        env_info['env_name'] = env_name
    with open(env_file, 'w') as env_yaml:
        env_yaml.write(yaml.dump(env_info, default_flow_style=False))
