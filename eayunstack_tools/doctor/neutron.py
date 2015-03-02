#check neutron

def neutron(parser):
    print "check neutron module"

def make(parser):
    '''Check Neutron'''
    parser.set_defaults(func=neutron)
