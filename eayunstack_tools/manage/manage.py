#encoding: utf-8

import pkg_resources

def make(parser):
    '''EayunStack Management'''
    subp=parser.add_subparsers()
    entry_points = [
        (e.name, e.load()) for e in pkg_resources.iter_entry_points('manage_command')
    ]
    for (name, fn) in entry_points:
        # 这里是添加子解析器
        p = subp.add_parser(
            name,
            description=fn.__doc__,
            help=fn.__doc__,
        )
        fn(p)
    return parser
