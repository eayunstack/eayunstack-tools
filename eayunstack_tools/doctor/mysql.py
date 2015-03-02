#check mysql

def mysql(parser):
    print "check mysql module"

def make(parser):
    '''Check MySQL'''
    parser.set_defaults(func=mysql)
