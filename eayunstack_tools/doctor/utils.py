import commands
from multiprocessing import Process, Pipe
from eayunstack_tools.utils import NODE_ROLE
from functools import wraps

from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.sys_utils import ssh_connect2

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

def run_doctor_cmd_on_node(role, node, cmd, pipe):
    LOG.info('%s%s Push check cmd to %-13s (%-10s) %s%s'
            % ('<', '='*2, node, role, '='*2, '>'))
    ssh_connect2(node, cmd, pipe=pipe)

'''
Use multiprocess to launch doctor check cmd on all node at the same time.
'''
def run_doctor_on_nodes(node_role, node_list, check_cmd):
    parent_conn, child_conn = Pipe()
    proc_list = []
    for node in node_list:
        proc=Process(target=run_doctor_cmd_on_node,
                    args=(node_role, node, check_cmd, child_conn,))
        proc.start()
        proc_list.append(proc)
    return proc_list, parent_conn
