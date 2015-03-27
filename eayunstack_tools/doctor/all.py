#check all object
from eayunstack_tools.doctor import env, cls, stack

def check_all(parser):
    print "check all object"
    env.check_all()
    cls.check_all()
    stack.check_all()

def make(parser):
    '''Check All Object'''
    parser.set_defaults(func=check_all)
