import pkg_resources
from functools import wraps
import logging
import logger

LOG = logging.getLogger(__name__)


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


def get_roles():
    """Get roles which node represents"""
    role_file_path = '/.node-role'
    roles = []
    try:
        with open(role_file_path, 'r') as f:
            for i in f:
                r = i.strip().split('\n')
                if r[0].lower() == 'fuel':
                    roles.append(ROLES.FUEL)
                elif r[0].lower() == 'controller':
                    roles.append(ROLES.CONTROLLER)
                elif r[0].lower() == 'compute':
                    roles.append(ROLES.CONTROLLER)
                elif r[0].lower() == 'ceph-osd':
                    roles.append(ROLES.CEPH_OSD)
                elif r[0].lower() == 'mongo':
                    roles.append(ROLES.MONGO)
                else:
                    roles.append(ROLES.UNKNOWN)
    except Exception as e:
        # If the file not exists, or something wrong happens, we consume
        # the node is unknow, and fire a warn message
        LOG.warn('Unknow node, please fix the issue: %s', logger.fmt_excep_msg(e))
        roles.append(ROLES.UNKNOWN)
    return roles

ROLES = enum('FUEL', 'CONTROLLER', 'COMPUTE', 'CEPH_OSD', 'MONGO', 'UNKNOWN')
NODE_ROLE = get_roles()
