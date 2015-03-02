#check keystone

def keystone(parser):
    print "check keystone module"

def make(parser):
    '''Check Keystone'''
    parser.set_defaults(func=keystone)
