#check openstack compent
import logging
from eayunstack_tools.doctor import common, config, utils
from eayunstack_tools.utils import register_decorater, userful_msg
from eayunstack_tools.logger import fmt_print
from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.doctor.config import *
from eayunstack_tools.doctor.utils import get_node_role
from eayunstack_tools.doctor.stack_func import *
from eayunstack_tools.utils import NODE_ROLE

register = register_decorater()
node_roles = get_node_role()

def stack(parser):
    # if node role is "unknow", go back
    if NODE_ROLE.is_unknown():
        LOG.error('Can not confirm the node role!')
        return
    if not NODE_ROLE.is_fuel():
        if parser.CONTROLLER:
            if not NODE_ROLE.is_controller():
                cmd_warn('controller')
                return
        if parser.COMPUTE:
            if not NODE_ROLE.is_compute():
                cmd_warn('compute')
                return
        if parser.MONGO:
            if not NODE_ROLE.is_mongo():
                cmd_warn('mongo')
                return
    if parser.CONTROLLER or parser.COMPUTE or parser.MONGO:
        if parser.PROFILE and not parser.SERVICE and not parser.CHECK_ALL:
            if parser.CONTROLLER:
                check('controller', 'profile')
            if parser.COMPUTE:
                check('compute', 'profile')
            if parser.MONGO:
                check('mongo', 'profile')
        if parser.SERVICE and not parser.PROFILE and not parser.CHECK_ALL:
            if parser.CONTROLLER:
                check('controller', 'service')
            if parser.COMPUTE:
                check('compute', 'service')
            if parser.MONGO:
                check('mongo', 'service')
        if parser.SERVICE and parser.PROFILE or parser.CHECK_ALL or not parser.PROFILE and not parser.SERVICE:
            if parser.CONTROLLER:
                check('controller', 'all')
            if parser.COMPUTE:
                check('compute', 'all')
            if parser.MONGO:
                check('mongo', 'all')
        return
    # check all
    if parser.CHECK_ALL and parser.PROFILE and parser.SERVICE:
        check_all()
        return
    elif parser.CHECK_ALL and parser.PROFILE:
        check_all_profile()
        return
    elif parser.CHECK_ALL and parser.SERVICE:
        check_all_service()
        return
    elif parser.CHECK_ALL:
        check_all()
        return
    # check profile or service
    if parser.PROFILE:
        check_all_profile()
    if parser.SERVICE:
        check_all_service()

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
        help='Check All Controller Node',
    )
    parser.add_argument(
        '--compute',
        dest='COMPUTE',
        action='store_true',
        default=False,
        help='Check All Compute Node',
    )
    parser.add_argument(
        '--mongo',
        dest='MONGO',
        action='store_true',
        default=False,
        help='Check All Mongo Node',
    )
    common.add_common_opt(parser)
    parser.set_defaults(func=stack)

# check all component

# IMPORTANT: node include fuel
all_roles = ('controller','compute','mongo')

def check(role, obj):
   if NODE_ROLE.is_fuel():
       check_nodes(role, obj)
   else:
       if not eval('NODE_ROLE.is_%s' % role)():
           LOG.warn('This command can only run on fuel or %s node !' % role)
       else:
           if obj == 'all':
               eval('check_%s_%s' % (role, 'profile'))()
               eval('check_%s_%s' % (role, 'service'))()
           else:
               eval('check_%s_%s' % (role, obj))()


def check_all():
    '''Check All OpenStack Component'''
    if not NODE_ROLE.is_fuel():
        check_all_profile()
        check_all_service()
    else:
        for role in all_roles:
            check_nodes(role, 'all')

def check_all_profile():
    if NODE_ROLE.is_fuel():
        for role in all_roles:
            check_nodes(role, 'profile', multi_role=True)
    else:
        for node_role in node_roles:
           # print node_role
            if node_role != 'ceph_osd':
       	        eval('check_%s_profile' % node_role)()

def check_all_service():
    if NODE_ROLE.is_fuel():
        for role in all_roles:
            check_nodes(role, 'service', multi_role=True)
    else:
        for node_role in node_roles:
            if node_role != 'ceph_osd':
                eval('check_%s_service' % node_role)()

# check controller profile & service
@userful_msg()
@register
def check_controller_profile():
    check_node_profiles('controller')

@userful_msg()
@register
def check_controller_service():
    check_node_services('controller')

# check compute profile & service
@userful_msg()
@register
def check_compute_profile():
    check_node_profiles('compute')

@userful_msg()
@register
def check_compute_service():
    check_node_services('compute')

# check mongo profile & service
@userful_msg()
@register
def check_mongo_profile():
    check_node_profiles('mongo')

@userful_msg()
@register
def check_mongo_service():
    check_node_services('mongo')

def cmd_warn(node_role):
    LOG.warn('This command can only run on fuel or %s node !' % node_role)
