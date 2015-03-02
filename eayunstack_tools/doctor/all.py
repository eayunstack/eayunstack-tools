#check all object
import ntp, mysql, nova

def check_all(parser):
    print "check all object"
    ntp.ntp(parser)
    mysql.mysql(parser)
    nova.nova(parser)

def make(parser):
    '''Check All Object'''
    parser.set_defaults(func=check_all)
