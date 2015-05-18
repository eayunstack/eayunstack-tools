import socket
import struct
import logging
from fuelclient.objects.environment import Environment

from eayunstack_tools.logger import StackLOG as LOG


def ceph_cluster_network(parser):
    update_facts(parser.env, parser.cidr, parser.nic_mappings)


def make(parser):
    """
    Configure ceph cluster network
    """
    parser.add_argument(
        '--env',
        required=True,
        help='The fuel environment to be edited.'
    )
    parser.add_argument(
        '--cidr',
        required=True,
        help='CIDR for the ceph cluster network.'
    )
    parser.add_argument(
        '--nic_mappings',
        required=True,
        help='Node and nic mappings in the format of NODE-ID:NIC, '
             'separated by commas.'
    )
    parser.set_defaults(func=ceph_cluster_network)


def _get_network_base(network_cidr):
    try:
        network, mask = network_cidr.split('/')
        mask = int(mask)
        if mask <= 0 or mask >= 32:
            raise ValueError
        network_i = struct.unpack(
            '!I', socket.inet_pton(socket.AF_INET, network)
        )[0]
        network_base = network_i - network_i % (2**(32-mask))
    except (socket.error, ValueError):
        msg = 'Wrong CIDR specified: %s.' % network_cidr
        LOG.error(msg)
        raise RuntimeError(msg)
    return network_base


def _parse_nic_mappings(nic_mappings):
    node_nic_mappings = dict()

    try:
        for m in nic_mappings.split(','):
            node, nic = m.split(':')
            node_nic_mappings[node] = nic
    except ValueError:
        msg = 'Wrong NIC mappings specified: %s.' % nic_mappings
        LOG.error(msg)
        raise RuntimeError(msg)

    return node_nic_mappings


def update_facts(env, cidr, nic_mappings):

    # silent keystoneclient logs
    for handler in LOG.logger.handlers:
        if type(handler) == logging.StreamHandler:
            handler.addFilter(logging.Filter('root'))

    e = Environment(env)
    network_data = e.get_network_data()
    storage_network = filter(
        lambda network: network['name'] == 'storage',
        network_data['networks'])[0]
    storage_network_base = _get_network_base(storage_network['cidr'])

    cluster_network_base = _get_network_base(cidr)
    cluster_network_mask = cidr.split('/')[1]

    node_nic_mappings = _parse_nic_mappings(nic_mappings)

    facts = e.get_default_facts('deployment')

    for fact in facts:
        if fact['role'] != 'ceph-osd':
            continue

        LOG.info('Updating node %s.' % fact['uid'])
        network_scheme = fact['network_scheme']

        roles = network_scheme['roles']
        roles['ceph_cluster'] = 'br-ceph-cluster'
        LOG.info('New role added: %s.' % roles['ceph_cluster'])

        endpoints = network_scheme['endpoints']
        storage_ip = endpoints['br-storage']['IP'][0].split('/')[0]
        host_id = struct.unpack(
            '!I', socket.inet_pton(socket.AF_INET, storage_ip)
        )[0] - storage_network_base
        cluster_network_ip = "%s/%s" % (
            socket.inet_ntop(
                socket.AF_INET,
                struct.pack('!I', cluster_network_base + host_id)
            ),
            cluster_network_mask
        )
        endpoints['br-ceph-cluster'] = {
            'IP': [cluster_network_ip],
            'other_nets': []
        }
        LOG.info('New endpoint added: %s.' % endpoints['br-ceph-cluster'])

        transformations = network_scheme['transformations']
        nic = node_nic_mappings[fact['uid']]
        del node_nic_mappings[fact['uid']]
        lower_br = 'br-%s' % nic
        upper_br = 'br-ceph-cluster'

        add_lower_br = {'action': 'add-br', 'name': lower_br}
        add_upper_br = {'action': 'add-br', 'name': upper_br}
        add_port = {'action': 'add-port', 'bridge': lower_br, 'name': nic}
        add_patch = {'action': 'add-patch', 'bridges': [upper_br, lower_br],
                     'trunks': [0]}
        for act in [add_lower_br, add_upper_br, add_port, add_patch]:
            if act not in transformations:
                LOG.info('Adding %s into network transformations.' % act)
                transformations.append(act)

    if len(node_nic_mappings) > 0:
        missings = ', '.join(node_nic_mappings.keys())
        msg = 'The following nodes are not with role ceph-osd: %s' % missings
        LOG.error(msg)
        raise RuntimeError(msg)

    LOG.info('Uploading new facts to fuel server...')
    e.upload_facts('deployment', facts)
    LOG.info('Ceph cluster network has been successfully configured!')
