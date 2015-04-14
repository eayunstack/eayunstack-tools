import commands
import logging
from eayunstack_tools.utils import NODE_ROLE

LOG = logging.getLogger(__name__)

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
        LOG.info('   Service %s is running ...', name)
    else:
        LOG.error('   Service %s is not running ...', name)

    (_, out) = commands.getstatusoutput(
        'systemctl is-enabled %s.service' % (name))
    if out == 'enabled':
        LOG.info('   Service %s is enabled ...', name)
    else:
        LOG.error('   Service %s is not enabled ...', name)

def check_process(name):
    (status, out) = commands.getstatusoutput('pgrep -lf %s' % (name))
    if status == 0:
        # fmt_print('%s is running' % (name))
        pass
    else:
        LOG.error('%s is not running', name)
