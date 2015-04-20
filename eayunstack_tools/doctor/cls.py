#check cluster status
from eayunstack_tools.doctor import common
import logging

LOG = logging.getLogger(__name__)

def cls(parser):
    print "check cluster module"
    if parser.CHECK_ALL:
        check_all()
    if parser.CLUSTER_NAME == 'rabbitmq':
        check_rabbitmq()

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
    print 'check rabbitmq'
