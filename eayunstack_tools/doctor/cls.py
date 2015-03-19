#check cluster status
from eayunstack_tools.doctor import common

def cls(parser):
    print "check cluster module"
    if parser.CHECK_ALL:
        check_all()

def make(parser):
    '''Check cluster'''
    parser.add_argument(
        '-n',
        dest='CLUSTER_NAME',
        choices=['mysql','rabbit','ceph','pacemaker'],
        help='Cluster Name',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=cls)

def check_all():
    '''Check All Cluster'''
    print "Check All Cluster"
