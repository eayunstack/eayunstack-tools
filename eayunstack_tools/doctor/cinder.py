#check cinder

def cinder(parser):
    print "check cinder module"

def make(parser):
    '''Check Cinder'''
    parser.set_defaults(func=cinder)
