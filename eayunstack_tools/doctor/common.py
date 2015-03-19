# doctor command common options

def add_common_opt(parser):
    parser.add_argument(
        '-a',
        dest='CHECK_ALL',
        action='store_true',
        default=False,
        help='Check ALL',
    )
    parser.add_argument(
        '-o',
        dest='FILENAME',
        help='Local File To Save Output Info',
    )
    return parser
