import commands
import logging
from eayunstack_tools.utils import NODE_ROLE
from eayunstack_tools.logger import fmt_print

from eayunstack_tools.logger import StackLOG as LOG

def search_service(service):
    (s, out) = commands.getstatusoutput('systemctl list-unit-files | grep "%s"' %(service))
    return s

def get_node_role():
    node_roles = []
    if NODE_ROLE.is_unknown():
        return node_roles
    if NODE_ROLE.is_fuel():
        node_roles.append('fuel')
    if NODE_ROLE.is_controller():
        node_roles.append('controller')
    if NODE_ROLE.is_compute():
        node_roles.append('compute')
    if NODE_ROLE.is_ceph_osd():
        node_roles.append('ceph_osd')
    if NODE_ROLE.is_mongo():
        node_roles.append('mongo')
    return node_roles
    

def check_service(name):
    (_, out) = commands.getstatusoutput(
        'systemctl is-active %s.service' % (name))
    if out == 'active':
        fmt_print('Service %s is running ...' % name)
    else:
        LOG.error('Service %s is not running ...' % name)

    (_, out) = commands.getstatusoutput(
        'systemctl is-enabled %s.service' % (name))
   # if out == 'enabled':
    if 'enabled' in out:
        fmt_print('Service %s is enabled ...' % name)
    else:
        LOG.error('Service %s is not enabled ...' % name)

def check_process(name):
    (status, out) = commands.getstatusoutput('pgrep -lf %s' % (name))
    if status == 0:
        # fmt_print('%s is running' % (name))
        pass
    else:
        LOG.error('%s is not running' % name)
