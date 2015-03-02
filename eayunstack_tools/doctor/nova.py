#check nova

def nova(parser):
    print "check nova module"

def make(parser):
    '''Check Nova'''
    parser.set_defaults(func=nova)
