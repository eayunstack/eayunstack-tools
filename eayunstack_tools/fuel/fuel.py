#encoding: utf-8

#import argparse
#import sys
import pkg_resources

#def fuel(parser):
#    print "Bakup number: %s" % parser.number
#    print parser.get_subparsers()
#    if parser.backup :
#    print "refrence fuel module"
#    pass

def make(parser):
    '''EayunStack fuel management'''
    subp=parser.add_subparsers()
    entry_points = [
        (e.name, e.load()) for e in pkg_resources.iter_entry_points('fuel_command')
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
#    fuel_backup=subparsers.add_parser('backup',help='Fuel Backup')
#    fuel_backup.add_argument(
#        '--number',
#        help="backup number",
#    )
#    fuel_restore=subparsers.add_parser('restore',help='Fuel Restore')
#    fuel_restore.add_argument(
#        '--file',
#        help="Restore from file",
#    )
#    parser.set_defaults(func=fuel)
