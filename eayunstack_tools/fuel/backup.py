#fuel backup

def backup(parser):
    print "fuel backup module"
    print "Backup Number: %s" % parser.number

def make(parser):
    '''Fuel Backup'''
    parser.add_argument(
        '--number',
        help='backup number')
    parser.set_defaults(func=backup)
