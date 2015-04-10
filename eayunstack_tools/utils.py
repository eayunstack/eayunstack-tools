import pkg_resources
from functools import wraps
import logging
import logger

LOG = logging.getLogger()


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


def register_decorater():
    reg = []

    def decorater(f):
        reg.append(f.__name__)
        return f

    decorater.all = reg
    return decorater


def userful_msg():
    def decorate(f):
        @wraps(f)
        def newfunc(*a, **kw):
            LOG.info('%s start running %s %s', '='*10, f.__name__, '='*10)
            ret = f(*a, **kw)
            return ret
        return newfunc

    return decorate


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


ROLES = enum('FUEL', 'CONTROLLER', 'COMPUTE', 'CEPH_OSD', 'MONGO', 'UNKNOWN')


class NodeRole(object):
    def __init__(self, role_file_path='/.node-role'):
        self._role_file_path = role_file_path
        self._roles = self._get_roles()

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
                        roles.append(ROLES.UNKNOWN)
        except Exception as e:
            # If the file not exists, or something wrong happens, we consume
            # the node is unknow, and fire a warn message
            LOG.warn('Unknow node, please fix the issue: %s',
                     logger.fmt_excep_msg(e))
            roles.append(ROLES.UNKNOWN)
        return roles

    @property
    def node_role(self):
        return self._roles

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

    def _node_list(self):
        from fuelclient.client import APIClient
        LOG.setLevel(logging.CRITICAL)
        nodes = []
        rep = APIClient.get_request("nodes/")
        for n in rep:
            roles = ' '.join(i for i in n['roles'])
            if not roles:
                roles = 'unused'
            host = n['fqdn']
            ip = n['ip']
            mac = n['mac']
            nodes.append({'roles': roles, 'host': host, 'ip': ip, 'mac': mac})
        # FIXME: our log level is DEBUG?
        LOG.setLevel(logging.DEBUG)

        def _cmp(s):
            return s['roles']
        return sorted(nodes, key=_cmp)

    @property
    def nodes(self):
        if self.is_fuel():
            # just fuel node need know node list
            return self._node_list()
        else:
            raise RuntimeError

NODE_ROLE = NodeRole()
