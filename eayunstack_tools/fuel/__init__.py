import pkg_resources

def make(parser):
    '''EayunStack Fuel Management'''
    subp=parser.add_subparsers(
        title='Commands',
        metavar='COMMAND',
        help='description',
        )

    entry_points = [
        (e.name, e.load()) for e in pkg_resources.iter_entry_points('fuel_command')
    ]
    for (name, fn) in entry_points:
        p = subp.add_parser(
            name,
            description=fn.__doc__,
            help=fn.__doc__,
        )
        fn(p)
    return parser
