#ami management

def ami(parser):
    print "reference module"

def make(parser):
    '''AMI Image Management'''
    parser.add_argument(
        '--kernel-file',
        action='store',
        dest='KERNEL_FILE',
        help='The path of kernel file you want to use'
    )
    parser.add_argument(
        '--initrd-file',
        action='store',
        dest='INITRD_FILE',
        help='The path of initrd file you want to use'
    )
    parser.add_argument(
        '--imange-file',
        action='store',
        dest='IMAGE_FILE',
        help='The path of image file you want to upload'
    )
    parser.add_argument(
        '-n',
        '--name',
        action='store',
        dest='NAME',
        help='The AMI image name'
    )
    parser.set_defaults(func=ami)

def AMI_image_upload():
    '''AMI Image Upload'''
    print "AMI image upload"
