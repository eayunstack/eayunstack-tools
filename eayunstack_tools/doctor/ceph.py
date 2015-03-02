#check ceph

def ceph(parser):
    print "check ceph module"

def make(parser):
    '''Check Ceph'''
    parser.set_defaults(func=ceph)
