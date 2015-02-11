#encoding: utf-8

def ntp(parser):
    print "check ntp module"

def make_ntp(parser):
    parser.set_defaults(func=ntp)
#    print "make_ntp"
