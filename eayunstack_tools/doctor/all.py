#check all object
import logging
from eayunstack_tools.doctor import env, cls, stack

from eayunstack_tools.logger import StackLOG as LOG

def check_all(parser):
    LOG.info('%s %-27s %s' % ('+'*13, 'Check Basic Environment', '+'*13))
    env.check_all()
    LOG.info('%s %-27s %s' % ('+'*13, 'Check Cluster Environment', '+'*13))
    cls.check_all()
    LOG.info('%s %-27s %s' % ('+'*13, 'Check OpenStack Environment', '+'*13))
    stack.check_all()

def make(parser):
    '''Check All Object'''
    parser.set_defaults(func=check_all)
