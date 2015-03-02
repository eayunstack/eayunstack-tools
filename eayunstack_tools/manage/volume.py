#volume management

def volume(parser):
    print "reference module"

def make(parser):
    '''Volume Management'''
    parser.add_argument(
        '-l',
        '--list-errors',
        action='store_const',
        const='list_errors',
        help='List Error Volumes'
    )
    parser.add_argument(
        '-d',
        '--destroy-volume',
        action='store_const',
        const='destroy_volume',
        help='Destroy Error Volumes'
    )
    parser.add_argument(
        '--id',
        help='Volumes ID'
    )
    parser.set_defaults(func=volume)

def list_errors():
    print "List Error Volume"

def destroy_volume(volume_id):
    print "Destroy Error Volume: %s" % volume_id
