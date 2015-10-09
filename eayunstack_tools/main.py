import argparse
import sys
import pkg_resources
import os
from eayunstack_tools.logger import StackLOG
from eayunstack_tools.utils import NODE_ROLE


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

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        dest='DEBUG',
        default=False,
        help='Log debug message or not',
    )

    parser.add_argument(
        '-e', '--email',
        dest='EMAIL',
        help='email address which send error log to(use commas to separate multiple email address)',
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
        if name == 'manage' and not NODE_ROLE.is_controller():
            continue
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

    StackLOG.open(args.FILENAME, args.DEBUG, args.EMAIL)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        pass
    finally:
        StackLOG.close()
