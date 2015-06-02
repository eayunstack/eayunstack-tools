#!encoding: utf-8

import logging
from prettytable import PrettyTable
from eayunstack_tools.utils import NODE_ROLE


logger = logging.getLogger()


def node_list(parser):
    t = PrettyTable(['Roles', 'Hosts', 'IP', 'MAC'], sortby='Roles')
    for node in NODE_ROLE.nodes:
        t.add_row([node['roles'], node['host'], node['ip'], node['mac']])
    print t


def make(parser):
    '''List OpenStack Node'''
    parser.set_defaults(func=node_list)
