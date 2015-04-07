#!encoding: utf-8

from fuelclient.client import APIClient
import logging
from prettytable import PrettyTable


logger = logging.getLogger()


def node_list(parser):
    logger.setLevel(logging.CRITICAL)
    # TODO: get fuel host from config file?
    rep = APIClient.get_request("nodes/")
    t = PrettyTable(['Roles', 'Hosts', 'IP', 'MAC'], sortby='Roles')
    for node in rep:
        roles = ' '.join(i for i in node['roles'])
        if not roles:
            roles = 'unused'
        host = node['fqdn']
        ip = node['ip']
        mac = node['mac']
        print roles, host, ip, mac
        t.add_row([roles, host, ip, mac])
    print t


def make(parser):
    '''List OpenStack Node'''
    parser.set_defaults(func=node_list)
