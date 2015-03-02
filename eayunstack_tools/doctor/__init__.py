import pkg_resources
import sys

def make(parser):
    '''EayunStack Doctor'''
    subp = parser.add_subparsers(
        title='Commands',
        metavar='COMMAND',
        help='description',
        )

    entry_points = [
        (e.name, e.load()) for e in pkg_resources.iter_entry_points('doctor_command')
    ]
    for (name, fn) in entry_points:
        p = subp.add_parser(
            name,
            description=fn.__doc__,
            help=fn.__doc__,
        )
        fn(p)
    return parser
