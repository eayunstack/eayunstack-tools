#check ntp

def ntp(parser):
    print "check ntp module"

def make(parser):
    '''Check NTP'''
    parser.set_defaults(func=ntp)
