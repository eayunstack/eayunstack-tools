#encoding: utf-8

def instance(parser):
    print "reference module"

def make_instance(parser):
    '''Instance Management'''
    parser.add_argument(
        '-l',
        '--list-errors',
        action='store_const',
        const='list_errors',
        help='List Error Instances'
    )
    parser.add_argument(
        '-d',
        '--destroy-instance',
        action='store_const',
        const='destroy_instance',
        help='Destroy Error Instances'
    )
    parser.add_argument(
        '--id',
        help='Instances ID'
    )
    parser.set_defaults(func=instance)

def list_errors():
    print "List Error Instance"

def destroy_instance(instance_id):
    print "Destroy Error Instance: %s" % instance_id
