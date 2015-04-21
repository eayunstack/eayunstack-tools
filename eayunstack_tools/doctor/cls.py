#check cluster status
from eayunstack_tools.doctor import common
from eayunstack_tools.utils import NODE_ROLE, get_controllers_hostname
from eayunstack_tools.doctor.cls_func import get_rabbitmq_nodes, get_mysql_nodes
import logging

LOG = logging.getLogger(__name__)

def cls(parser):
    print "check cluster module"
    if parser.CHECK_ALL:
        check_all()
    if parser.CLUSTER_NAME == 'rabbitmq':
        check_rabbitmq()
    if parser.CLUSTER_NAME == 'mysql':
        check_mysql()

def make(parser):
    '''Check cluster'''
    parser.add_argument(
        '-n',
        dest='CLUSTER_NAME',
        choices=['mysql','rabbitmq','ceph','pacemaker'],
        help='Cluster Name',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=cls)

def check_all():
    '''Check All Cluster'''
    print "Check All Cluster"

def check_rabbitmq():
    # node role check
    if not NODE_ROLE.is_fuel():
        if not NODE_ROLE.is_controller():
            LOG.warn('This command can only run on fuel or controller node !')
            return
    # get all controller node hostname
    controllers = get_controllers_hostname()
    if controllers is None:
        LOG.error('Can not get the controllers node list !')
        return
    # get masters & slaves node list
    masters = get_rabbitmq_nodes('masters')
    slaves = get_rabbitmq_nodes('slaves')
    running_nodes = masters + slaves
    if running_nodes is None:
        LOG.error('Can not get the running node list for rabbitmq cluster !')
        return
    # check all controller nodes in masters + slaves node list
    error_nodes = []
    for node in controllers:
        if node not in running_nodes:
            error_nodes.append(node)

    if error_nodes:
        LOG.error('Node %s not in rabbitmq cluster !' % error_nodes)
        LOG.error('Rabbitmq cluster check faild !')
    else:
        LOG.info('Rabbitmq cluster check successfully !')

def check_mysql():
    print 'check mysql'
    # node role check
    if not NODE_ROLE.is_fuel():
        if not NODE_ROLE.is_controller():
            LOG.warn('This command can only run on fuel or controller node !')
            return
    # get running node list for mysql cluster
    running_nodes = get_mysql_nodes()
    if running_nodes is None:
        LOG.error('Can not get the running node list for rabbitmq cluster !')
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
