#encoding: utf-8

def backup(parser):
    print "fuel backup module"
    print "Backup Number: %s" % parser.number

def make_backup(parser):
    parser.add_argument(
        '--number',
        help='backup number')
    parser.set_defaults(func=backup)
#    print "make_backup"
