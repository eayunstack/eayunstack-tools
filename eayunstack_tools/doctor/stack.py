#check openstack compent
from eayunstack_tools.doctor import common

def stack(parser):
    print "check openstack compent module"
    if parser.CHECK_ALL:
        check_all()

def make(parser):
    '''Check OpenStack Compent'''
    parser.add_argument(
        '--profile',
        dest='PROFILE',
        action='store_true',
        default=False,
        help='Check Profile',
    )
    parser.add_argument(
        '--service',
        dest='SERVICE',
        action='store_true',
        default=False,
        help='Check Service Status',
    )
    parser.add_argument(
        '--controller',
        dest='CONTROLLER',
        action='store_true',
        default=False,
        help='Check Controller Node',
    )
    parser.add_argument(
        '--network',
        dest='NETWORK',
        action='store_true',
        default=False,
        help='Check Network Node',
    )
    parser.add_argument(
        '--compute',
        dest='COMPUTE',
        action='store_true',
        default=False,
        help='Check Compute Node',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=stack)

def check_all():
    '''Check All OpenStack Compent'''
    print "Check All OpenStack Compent"
