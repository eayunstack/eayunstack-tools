#check environment
import logging
from eayunstack_tools.doctor import common
from eayunstack_tools.doctor import ntp, selinux, disk, network
from eayunstack_tools.doctor.utils import set_logger, register_decorater, userful_msg, fmt_print

LOG = logging.getLogger(__name__)

register = register_decorater()

def env(parser):
    set_logger()
    if parser.CHECK_ALL:
        check_all()
    if parser.OBJECT_NAME == 'ntp':
        check_ntp()
    if parser.OBJECT_NAME == 'selinux':
        check_selinux()
    if parser.OBJECT_NAME == 'disk':
        check_disk()
    if parser.OBJECT_NAME == 'network':
        check_network()
        

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
    LOG.debug('This option will do following things:')
    for i in register.all:
        fmt_print('--' + i)
    for i in register.all:
        eval(i)()

@userful_msg()
@register
def check_ntp():
    ntp.check_ntp(LOG)


@userful_msg()
@register
def check_selinux():
    selinux.check_selinux(LOG)

@userful_msg()
@register
def check_disk():
    disk.check_disk(LOG)

@userful_msg()
@register
def check_network():
    network.check_network(LOG)
