#encoding: utf-8

def mysql(parser):
    print "check mysql module"

def make_mysql(parser):
    parser.set_defaults(func=mysql)
#    print "make_mysql"
