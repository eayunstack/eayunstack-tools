#encoding: utf-8

def restore(parser):
    print "fuel restore"

def make_restore(parser):
    parser.set_defaults(func=restore)
#    print "fuel make_restore"
