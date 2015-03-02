#check glance

def glance(parser):
    print "check glance module"

def make(parser):
    '''Check Glance'''
    parser.set_defaults(func=glance)
