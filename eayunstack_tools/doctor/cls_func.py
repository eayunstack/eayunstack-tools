from eayunstack_tools.utils import get_node_list, ssh_connect2
import commands
import re
from eayunstack_tools.logger import StackLOG as LOG


# get node list for rabbitmq cluster
def get_rabbitmq_nodes():
    running_nodes = []
    (s, o) = commands.getstatusoutput('crm_resource --locate --resource clone_p_rabbitmq-server 2> /dev/null | grep "running on"')
    if s != 0 or o is None:
        return
    else:
        for entry in o.split('\n'):
            running_nodes.append(entry.split()[5])
    return running_nodes



# get running node list for mysql cluster
def get_mysql_nodes():
    running_nodes = []
    (s, o) = commands.getstatusoutput('crm_resource --locate --resource clone_p_mysql 2> /dev/null | grep "running on"')
    if s != 0 or o is None:
        return
    else:
        for entry in o.split('\n'):
            running_nodes.append(entry.split()[5])
    return running_nodes

# get running node list for haproxy cluster
def get_haproxy_nodes():
    running_nodes = []
    (s, o) = commands.getstatusoutput('crm_resource --locate --resource clone_p_haproxy 2> /dev/null | grep "running on"')
    if s != 0 or o is None:
        return
    else:
        for entry in o.split('\n'):
            running_nodes.append(entry.split()[5])
    return running_nodes

# get ceph cluster status
def get_ceph_health():
    (s, o) = commands.getstatusoutput('ceph health')
    if s != 0:
        return False
    else:
        if o == 'HEALTH_OK':
            return True
        else:
            return False

# get ceph osd status
def get_ceph_osd_status():
    (s, o) = commands.getstatusoutput('ceph osd tree')
    if s != 0 or o is None:
        return
    else:
        return o

# check all nodes
def check_all_nodes(check_obj):
    if check_obj is 'all':
        check_cmd = 'sudo eayunstack doctor cls --all'
    else:
        check_cmd = 'sudo eayunstack doctor cls -n %s' % check_obj
    # get controller node list
    node_list = get_node_list('controller')
    # ssh to all controller node to check obj
    if len(node_list) == 0:
        LOG.warn('Node list is null !')
        return
    else:
        for node in node_list:
            LOG.info('%s Role: %-10s Node: %-13s %s' % ('*'*15, 'controller', node, '*'*15))
            ssh_connect2(node, check_cmd)
