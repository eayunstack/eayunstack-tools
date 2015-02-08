#!/usr/bin/python
#encoding: utf-8
import argparse
import sys
import pkg_resources

def create_parser():
    parser = argparse.ArgumentParser(
        prog='eayunstack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""EayunStack Management Tools.\n\n""",
        )

    sub = parser.add_subparsers(
        title='Commands',
        metavar='COMMAND',
        help='description',
        )

    entry_points = [
        (e.name, e.load()) for e in pkg_resources.iter_entry_points('command')
    ]
    for (name, fn) in entry_points:
        # 这里是添加子解析器, 具体请看 argparse 的文档
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

    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
