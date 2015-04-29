# check environment
import logging
import commands
import re
import os
import math
import glob
from eayunstack_tools.doctor import common
from eayunstack_tools.utils import register_decorater, userful_msg, get_node_list, ssh_connect
from eayunstack_tools.logger import fmt_print, valid_print
from utils import check_service
from eayunstack_tools.utils import NODE_ROLE

LOG = logging.getLogger(__name__)
register = register_decorater()


def env(parser):
    if NODE_ROLE.is_unknown():
        LOG.error('Can not confirm the node role!')
        return
    if parser.CHECK_ALL:
        check_all()
    elif parser.OBJECT_NAME:
        object_func = 'check_%s' % (parser.OBJECT_NAME)
        eval(object_func)()
    else:
        # TODO: print usage
        pass


def make(parser):
    '''Check Environment Object'''
    # choices is something like ['ntp', 'selinux', 'disk', 'network'],
    # which depends on the functions you define below
    parser.add_argument(
        '-n',
        dest='OBJECT_NAME',
        choices=[i.split('_')[1] for i in register.all],
        help='Object Name',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=env)


def check_all():
    '''Check All Environement Object'''
    if NODE_ROLE.is_fuel():
        node_list = get_node_list('all')
        for node in node_list:
            LOG.info('%s Node: %-13s %s' % ('*'*15, node, '*'*15))
            out,err = ssh_connect(node, 'eayunstack doctor env -a')
            if out:
                print out
            else:
                LOG.error('Check failed !')
                print err
    else:
        LOG.debug('This option will do following things:')
        for i in register.all:
            fmt_print('--' + i)
        for i in register.all:
            eval(i)()


@userful_msg()
@register
def check_ntp():
    check_service('ntpd')
    (s, out) = commands.getstatusoutput(
        'ntpstat | grep "synchronised to NTP server"')
    if s != 0:
        LOG.error('ntpstat error, please check it')
        return
    else:
        p = re.compile(r'.+\((.+)\).+')
        try:
            server = p.match(out).groups()[0]
            LOG.info('ntpserver is %s', server)
        except:
            LOG.error('except ntpstate error, please check it')
            return


@userful_msg()
@register
def check_selinux():
    # Correct state [enforcing, permissive, disabled]
    correct_state = correct_conf = "disabled"

    # check current state
    (s, out) = commands.getstatusoutput('getenforce')
    current_state = out
    if s != 0:
        LOG.error('getenforce error, please check it')
    else:
        if current_state == correct_state.capitalize():
            LOG.info('SELinux current state is: %s' % current_state)
        else:
            LOG.warn('SELinux current state is: %s' % current_state)
            LOG.error('SELinux state need to be %s ' %
                      correct_state.capitalize())

    # check profile /etc/sysconfig/selinux
    current_conf = commands.getoutput(
        'grep "^SELINUX=" /etc/sysconfig/selinux | cut -d "=" -f 2')
    if current_conf == correct_conf:
        LOG.info('SELinux current conf in profile is: %s' % current_conf)
    else:
        LOG.warn('SELinux current conf in profile is: %s' % current_conf)
        LOG.error('SELinux configuration in profile need to be %s '
                  % correct_conf)


@userful_msg()
@register
def check_disk():
    limit = 85
    vfs = os.statvfs("/")
    # get "/" filesystem space used percent
    used_percent = int(math.ceil((
        float(vfs.f_blocks-vfs.f_bavail)/float(vfs.f_blocks))*100))
    if used_percent >= 0 and used_percent < limit:
        LOG.info('The "/" filesystem used %s%% space !' % used_percent)
    elif used_percent >= limit:
        LOG.warn('The "/" filesystem used %s%% space !' % used_percent)


@userful_msg()
@register
def check_network():
    # 1) find all network and their link status
    tmp = glob.glob('/sys/class/net/*/device')
    nics = dict()
    warn = False
    for i in tmp:
        name = i.split('/')[4]
        (status, out) = commands.getstatusoutput(
            "ethtool %s | \grep 'Link detected:'" % (name))
        if 'yes' in out:
            status = 'yes'
        else:
            status = 'no'
            warn = True
        nics[name] = status

    # TODO: print the function of nics, e.g. for managerment or storage
    if warn:
        LOG.warn('Network card information:')
    else:
        LOG.info('Network card information:')
    for i in nics.keys():
        valid_print(i, nics[i])

    # 2) check all NIC network connectivity

    # how to check ???
