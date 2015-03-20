#check environment
from eayunstack_tools.doctor import common
from eayunstack_tools.doctor import ntp

def env(parser):
    if parser.CHECK_ALL:
        check_all()
    if parser.OBJECT_NAME == 'ntp':
        ntp.check_ntp()
        

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
    ntp.check_ntp()
