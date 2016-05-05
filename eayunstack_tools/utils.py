import pkg_resources
import logger
import os
import platform
import logging
import yaml


def make_subcommand(parser, command):
    subp = parser.add_subparsers(
        title='Commands',
        metavar='COMMAND',
        help='DESCRIPTION',
        )

    entry_points = [
        (e.name, e.load())
        for e in pkg_resources.iter_entry_points(command + '_command')
    ]
    for (name, fn) in entry_points:
        p = subp.add_parser(
            name,
            description=fn.__doc__,
            help=fn.__doc__,
        )
        fn(p)
    return parser


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


ROLES = enum('FUEL', 'CONTROLLER', 'COMPUTE', 'CEPH_OSD', 'MONGO', 'UNKNOWN')


class NodeRole(object):
    def __init__(self):
        if os.path.exists('/.node-role'):
            role_file_path = '/.node-role'
        else:
            role_file_path = '/.eayunstack/node-role'
        self._role_file_path = role_file_path
        self._role_list_file_path = '/.eayunstack/node-list'
        self._roles = self._get_roles()
        self._get_hostname = platform.node()

    def _get_roles(self):
        """Get roles which node represents"""
        roles = []
        try:
            with open(self._role_file_path, 'r') as f:
                for i in f:
                    r = i.strip().split('\n')
                    if r[0].lower() == 'fuel':
                        roles.append(ROLES.FUEL)
                    elif r[0].lower() == 'controller':
                        roles.append(ROLES.CONTROLLER)
                    elif r[0].lower() == 'compute':
                        roles.append(ROLES.COMPUTE)
                    elif r[0].lower() == 'ceph-osd':
                        roles.append(ROLES.CEPH_OSD)
                    elif r[0].lower() == 'mongo':
                        roles.append(ROLES.MONGO)
                    else:
                        print 'Unknow node, please fix it'
                        roles.append(ROLES.UNKNOWN)
        except Exception as e:
            # If the file not exists, or something wrong happens, we consume
            # the node is unknow, and fire a warn message
            print 'Unknow node, please fix the issue: %s'\
                % logger.fmt_excep_msg(e)
            roles.append(ROLES.UNKNOWN)
        if not roles:
            print 'Unknow node, please fix it'
            roles.append(ROLES.UNKNOWN)
        return roles

    @property
    def node_role(self):
        return self._roles

    @property
    def role(self):
        if self.is_fuel():
            return 'fuel'
        elif self.is_controller():
            return 'controller'
        elif self.is_compute():
            return 'compute'
        elif self.is_ceph_osd():
            return 'ceph_osd'
        elif self.is_mongo():
            return 'mongo'
        elif self.is_unknown():
            return 'unknown'

    def is_fuel(self):
        return ROLES.FUEL in self.node_role

    def is_controller(self):
        return ROLES.CONTROLLER in self.node_role

    def is_compute(self):
        return ROLES.COMPUTE in self.node_role

    def is_ceph_osd(self):
        return ROLES.CEPH_OSD in self.node_role

    def is_mongo(self):
        return ROLES.MONGO in self.node_role

    def is_unknown(self):
        ROLES.UNKNOWN == self.node_role[0]

    def _node_list(self):
        nodes = []
        try:
            with open(self._role_list_file_path, 'r') as f:
                for i in f:
                    # i: "node-6.eayun.com:node-6:172.16.100.10:ceph-osd:52.a8.3b.dc.c9.47:192.168.1.239"
                    r = i.strip().split('\n')[0].split(':')
                    if len(r) != 6:
                        continue
                    nodes.append({'roles': r[3], 'host': r[0],
                                  'ip': r[2], 'mac': r[4].replace('.', ':'),
                                  'idrac_addr': r[5]})
        except Exception as e:
            print 'failed to open file: %s: %s' % (self._role_list_file_path,
                                                   logger.fmt_excep_msg(e))

        def _cmp(s):
            return s['roles']
        return sorted(nodes, key=_cmp)

    @property
    def nodes(self):
        return self._node_list()

    @property
    def hostname(self):
        return self._get_hostname

NODE_ROLE = NodeRole()


class log_disabled(object):
    def __enter__(self):
        logging.disable(logging.NOTSET)


    def __exit__(self, e_type, e_value, traceback):
        logging.disable(logging.INFO)


def get_controllers_hostname():
    file_path = '/.eayunstack/node-list'
    controllers = []
    if not os.path.exists(file_path):
        return
    node_list_file = open(file_path)
    try:
        for line in node_list_file:
            if 'controller' in line:
                line = line.split(':')[0]
                controllers.append(line)
    finally:
        node_list_file.close()
    return controllers


def get_node_list(role):
    node_list = []
    try:
        for node in NODE_ROLE.nodes:
            if role == 'all':
                node_list.append(node['host'])
            elif node['roles'] == role:
                node_list.append(node['host'])
    except:
        node_list = []
    return node_list

def logging_disable(func):
    def fn(*args, **kwargs):
        logging.disable(logging.INFO)
        r = func(*args, **kwargs)
        logging.disable(logging.NOTSET)
        return r
    return fn

@logging_disable
def get_fuel_node_ip(env):
    fuel_node_ip = None
    from fuelclient.objects.environment import Environment
    e = Environment(env)
    nodes_id = [x.data['id'] for x in e.get_all_nodes()]
    for fact in e.get_default_facts('deployment', [nodes_id[0]]):
        fuel_node_ip = fact['master_ip']
        if fuel_node_ip:
            break
    return fuel_node_ip

def get_public_vip():
    cfg = yaml.load(file('/etc/astute.yaml'))
    public_vip = cfg['public_vip']
    return public_vip
