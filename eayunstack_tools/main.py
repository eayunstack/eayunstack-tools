import argparse
import sys
import pkg_resources
from eayunstack_tools.logger import set_logger


def create_parser():
    parser = argparse.ArgumentParser(
        prog='eayunstack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""EayunStack Management Tools.\n\n""",
        )

    parser.add_argument(
        '-o', '--output',
        dest='FILENAME',
        help='Local File To Save Output Info',
    )

    sub = parser.add_subparsers(
        title='Commands',
        metavar='COMMAND',
        help='DESCRIPTION',
        )

    entry_points = [
        (e.name, e.load()) for e in pkg_resources.iter_entry_points('command')
    ]
    for (name, fn) in entry_points:
        p = sub.add_parser(
            name,
            description=fn.__doc__,
            help=fn.__doc__,
        )
        fn(p)
    return parser


def main():
    parser = create_parser()
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()
    else:
        args = parser.parse_args()

    set_logger(args.FILENAME)
    if sys.argv[1] != 'init':
        return args.func(args)
