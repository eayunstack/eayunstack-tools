#check all object
import logging
from eayunstack_tools.doctor import env, cls, stack

LOG = logging.getLogger(__name__)

def check_all(parser):
    LOG.info('%s %-27s %s' % ('+'*25, 'Check Basic Environment', '+'*25))
    env.check_all()
    LOG.info('%s %-27s %s' % ('+'*25, 'Check Cluster Environment', '+'*25))
    cls.check_all()
    LOG.info('%s %-27s %s' % ('+'*25, 'Check OpenStack Environment', '+'*25))
    stack.check_all()

def make(parser):
    '''Check All Object'''
    parser.set_defaults(func=check_all)
