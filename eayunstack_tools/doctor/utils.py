import commands
import logging

LOG = logging.getLogger(__name__)

def search_service(service):
    (s, out) = commands.getstatusoutput('systemctl list-unit-files | grep "%s"' %(service))
    return s

# maybe need rewrite 
def get_node_role():
    if search_service("openstack-keystone") == 0:
        return 'controller'
    elif search_service("openstack-nova-compute") == 0:
        return 'compute'
    elif search_service("docker") == 0:
        return 'fuel'
    else:
        return 'unknow'

def check_service(name):
    (_, out) = commands.getstatusoutput(
        'systemctl is-active %s.service' % (name))
    if out == 'active':
        LOG.info('Service %s is running ...', name)
    else:
        LOG.error('Service %s is not running ...', name)

    (_, out) = commands.getstatusoutput(
        'systemctl is-enabled %s.service' % (name))
    if out == 'enabled':
        LOG.info('Service %s is enabled ...', name)
    else:
        LOG.error('Service %s is not enabled ...', name)

def check_process(name):
    (status, out) = commands.getstatusoutput('pgrep -lf %s' % (name))
    if status == 0:
        # fmt_print('%s is running' % (name))
        pass
    else:
        LOG.error('%s is not running', name)
