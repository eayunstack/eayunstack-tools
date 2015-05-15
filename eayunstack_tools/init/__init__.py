import sys
import logging
import os
from fuelclient.client import APIClient
from eayunstack_tools.utils import scp_connect
from eayunstack_tools.logger import StackLOG as LOG


def make(parser):
    '''EayunStack Environment Initialization'''
    parser.set_defaults(func=init)


def init(parser):
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
        entry = fqdn + ':' + host + ':' + ip + ':' + roles + '\n'
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
