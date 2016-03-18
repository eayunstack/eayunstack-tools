#check cluster status
from eayunstack_tools.doctor import common
from eayunstack_tools.utils import NODE_ROLE, get_controllers_hostname
from eayunstack_tools.doctor.cls_func import get_rabbitmq_nodes, get_mysql_nodes, get_haproxy_nodes, ceph_check_health, get_ceph_osd_status, check_all_nodes, get_crm_resource_list, get_crm_resource_running_nodes,get_ceph_space
from eayunstack_tools.doctor.cls_func import csv2dict
from eayunstack_tools.utils import get_public_vip
import logging
import urllib

from eayunstack_tools.logger import StackLOG as LOG

def cls(parser):
    if parser.CHECK_ALL:
        check_all()
    if parser.CLUSTER_NAME == 'rabbitmq':
        check_rabbitmq()
    if parser.CLUSTER_NAME == 'mysql':
        check_mysql()
    if parser.CLUSTER_NAME == 'haproxy':
        check_haproxy()
    if parser.CLUSTER_NAME == 'ceph':
        check_ceph()
    if parser.CLUSTER_NAME == 'pacemaker':
        check_pacemaker()
    if parser.CLUSTER_NAME == 'cephspace':
        check_cephspace()
    if parser.CLUSTER_NAME == 'haproxyresource':
        check_haproxyresource()

def make(parser):
    '''Check cluster'''
    parser.add_argument(
        '-n',
        dest='CLUSTER_NAME',
        choices=['mysql','rabbitmq','ceph','haproxy','pacemaker','cephspace','haproxyresource'],
        help='Cluster Name',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=cls)

def check_all():
    '''Check All Cluster'''
    # node role check
    if not NODE_ROLE.is_fuel():
        if not NODE_ROLE.is_controller():
            LOG.warn('This command can only run on fuel or controller node !')
            return
    if NODE_ROLE.is_fuel():
        check_all_nodes('all')
    else:
        check_rabbitmq()
        check_mysql()
        check_haproxy()
        check_ceph()
        check_pacemaker()
        check_cephspace()
        check_haproxyresource()

def check_rabbitmq():
    # node role check
    if not NODE_ROLE.is_fuel():
        if not NODE_ROLE.is_controller():
            LOG.warn('This command can only run on fuel or controller node !')
            return
    if NODE_ROLE.is_fuel():
        check_all_nodes('rabbitmq')
        return
    LOG.info('%s%s Checking rabbitmq cluster status' %('='*5, '>'))
    # get all controller node hostname
    controllers = get_controllers_hostname()
    if controllers is None:
        LOG.error('Can not get the controllers node list !')
        return
    # get masters & slaves node list
    running_nodes = get_rabbitmq_nodes()
    if running_nodes is None:
        LOG.error('Can not get the running node list for rabbitmq cluster !')
        return
    # check all controller nodes in masters + slaves node list
    error_nodes = []
    for node in controllers:
        if node.split('.')[0] not in running_nodes:
            error_nodes.append(node)

    if error_nodes:
        LOG.error('Node %s not in rabbitmq cluster !' % error_nodes)
        LOG.error('Rabbitmq cluster check faild !')
    else:
        LOG.info('Rabbitmq cluster check successfully !')

def check_mysql():
    # node role check
    if not NODE_ROLE.is_fuel():
        if not NODE_ROLE.is_controller():
            LOG.warn('This command can only run on fuel or controller node !')
            return
    if NODE_ROLE.is_fuel():
        check_all_nodes('mysql')
        return
    LOG.info('%s%s Checking mysql cluster status' %('='*5, '>'))
    # get running node list for mysql cluster
    running_nodes = get_mysql_nodes()
    if running_nodes is None:
        LOG.error('Can not get the running node list for mysql cluster !')
        return
    # get all controller node hostname
    controllers = get_controllers_hostname()
    if controllers is None:
        LOG.error('Can not get the controllers node list !')
        return
    # check all controller node in mysql cluster
    error_nodes = []
    for node in controllers:
        if node not in running_nodes:
            error_nodes.append(node)

    if error_nodes:
        LOG.error('Node %s is not running in mysql cluster !' % error_nodes)
        LOG.error('Mysql cluster check faild !')
    else:
        LOG.info('Mysql cluster check successfully !')

def check_haproxy():
    # node role check
    if not NODE_ROLE.is_fuel():
        if not NODE_ROLE.is_controller():
            LOG.warn('This command can only run on fuel or controller node !')
            return
    if NODE_ROLE.is_fuel():
        check_all_nodes('haproxy')
        return
    LOG.info('%s%s Checking haproxy cluster status' %('='*5, '>'))
    # get running node list for haproxy cluster
    running_nodes = get_haproxy_nodes()
    if running_nodes is None:
        LOG.error('Can not get the running node list for haproxy cluster !')
        return
    # get all controller node hostname
    controllers = get_controllers_hostname()
    if controllers is None:
        LOG.error('Can not get the controllers node list !')
        return
    # check all controller node in haproxy cluster
    error_nodes = []
    for node in controllers:
        if node not in running_nodes:
            error_nodes.append(node)

    if error_nodes:
        LOG.error('Node %s is not running in haproxy cluster !' % error_nodes)
        LOG.error('Haproxy cluster check faild !')
    else:
        LOG.info('Haproxy cluster check successfully !')

def check_ceph():
    # node role check
    if not NODE_ROLE.is_fuel():
        if not NODE_ROLE.is_controller():
            if not NODE_ROLE.is_ceph_osd():
                LOG.warn('This command can only run on fuel or controller or ceph-osd node !')
                return
    if NODE_ROLE.is_fuel():
        check_all_nodes('ceph')
        return
    # get cluster status
    LOG.info('%s%s Checking ceph cluster status' %('='*5, '>'))
    ceph_check_health()

    # check osd status
    LOG.info('%s%s Checking ceph osd status' %('='*5, '>'))
    check_success = True
    osd_status = get_ceph_osd_status()
    if not osd_status:
        LOG.error('Can not get ceph osd status !')
        check_success = False
    else:
        for l in osd_status.split('\n'):
            if 'id' not in l and 'weigh' not in l and 'osd.' in l:
                osd = l.split()[2]
                status = l.split()[3]
                if status != 'up':
                    LOG.error('%s status is not correct, please check it !' % osd)
                    check_success = False
    if check_success:
        LOG.info('Ceph osd status check successfully !')

def check_cephspace():
    # node role check
    if NODE_ROLE.is_controller():
        LOG.info('%s%s Checking ceph space' % ('='*5, '>'))
        ceph_space = get_ceph_space()
        limit_war = 83
        limit_error = 93
        if ceph_space >= 0 and ceph_space < limit_war:
            LOG.info('The ceph space is used: %s%%' % ceph_space)
        elif ceph_space >= limit_war and ceph_space < limit_error:
            LOG.warn('The ceph space is used: %s%%' % ceph_space)
    # Whe ceph_space Error ,The ceph_space return -1 
        elif ceph_space < 0: 
            LOG.error('The ceph space check error: Get ceph space Faild')
        else:
            LOG.error('The ceph space is used: %s%%' % ceph_space)

def check_pacemaker():
    if not NODE_ROLE.is_controller():
        LOG.warn('This command can only run on controller node !')
        return
    LOG.info('%s%s Checking pacemaker resource status' %('='*5, '>'))
    check_crm_resource_status()

def check_crm_resource_status():
    controllers = get_controllers_hostname()
    resource_list = get_crm_resource_list()
    for (resource, t) in resource_list:
        running_nodes = get_crm_resource_running_nodes(resource)
        if running_nodes is not None:
            if t == 'cp':
                error_nodes = []
                for node in controllers:
                    if node not in running_nodes:
                        error_nodes.append(node)
                if error_nodes:
                    LOG.error('Resource %s does not running on node %s !' % (resource, error_nodes))
                else:
                    LOG.info('Resource %s check successfully !' % resource)
            else:
                LOG.info('Resource %s check successfully !' % resource)
        else:
            LOG.error('Resource %s does not running on any node !' % resource)

def check_haproxyresource():
    monitor_url = get_haproxy_monitor_url()
    if not monitor_url:
        LOG.error('Can not get public vip in /etc/astute.yaml!')
        return
    monitor_content = get_haproxy_monitor_content(monitor_url)
    if not monitor_content:
        return
    resource_list = csv2dict(monitor_content)

    def _print_status(log_level='debug'):
        if check_status:
            eval('LOG.%s' % log_level)(\
                 '%s on %s status is %s, check_status is %s.'\
                 % (pxname, svname, status, check_status))
        else:
            eval('LOG.%s' % log_level)('%s on %s status is %s.'\
                 % (pxname, svname, status))

    for resource in resource_list:
        pxname = resource['pxname']
        svname = resource['svname']
        status = resource['status']
        check_status = resource['check_status']
        if svname == 'FRONTEND':
            if status == 'OPEN':
                _print_status()
            else:
                _print_status('error')
        else:
            if status == 'UP':
                _print_status()
            else:
                _print_status('error')

def get_haproxy_monitor_url():
    public_vip = get_public_vip()
    url = 'http://%s:10000/;csv;norefresh' % public_vip
    return url

def get_haproxy_monitor_content(url):
    content = None
    try:
        wp = urllib.urlopen(url)
        content = wp.read()
    except IOError:
        LOG.error('Can not connect to %s.' % url)
    finally:
        return content
        

