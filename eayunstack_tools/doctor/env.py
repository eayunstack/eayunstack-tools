#check environment
from eayunstack_tools.doctor import common

def env(parser):
    print "check environment module"
    if parser.CHECK_ALL:
        check_all()

def make(parser):
    '''Check Environment Object'''
    parser.add_argument(
        '-n',
        dest='OBJECT_NAME',
        choices=['ntp','network','selinux','disk'],
        help='Object Name',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=env)

def check_all():
    '''Check All Environement Object'''
    print "Check All Environment Object"
