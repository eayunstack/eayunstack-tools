import commands
from eayunstack_tools.utils import NODE_ROLE
from functools import wraps

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
        LOG.debug('Service %s is running ...' % name)
    else:
        LOG.error('Service %s is not running ...' % name)

    (_, out) = commands.getstatusoutput(
        'systemctl is-enabled %s.service' % (name))
    if 'enabled' in out:
        LOG.debug('Service %s is enabled ...' % name)
    else:
        LOG.error('Service %s is not enabled ...' % name)

def check_process(name):
    (status, out) = commands.getstatusoutput('pgrep -lf %s' % (name))
    if status == 0:
        LOG.debug('%s is running' % (name))
    else:
        LOG.error('%s is not running' % name)


def register_decorater():
    reg = []

    def decorater(f):
        reg.append(f.__name__)
        return f

    decorater.all = reg
    return decorater


def userful_msg():
    def decorate(f):
        @wraps(f)
        def newfunc(*a, **kw):
            LOG.debug('%s%s start running %s ' % ('='*5, '>', f.__name__))
            ret = f(*a, **kw)
            return ret
        return newfunc

    return decorate        
