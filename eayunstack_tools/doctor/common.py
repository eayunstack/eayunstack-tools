# doctor command common options


def add_common_opt(parser):
    parser.add_argument(
        '-a',
        '--all',
        dest='CHECK_ALL',
        action='store_true',
        default=False,
        help='Check ALL',
    )
