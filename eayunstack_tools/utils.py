import pkg_resources
from functools import wraps
import logging
import logger
import paramiko
import os
import socket

from eayunstack_tools.logger import StackLOG as LOG


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
            LOG.info('%s%s start running %s ', '='*5, '>', f.__name__)
            ret = f(*a, **kw)
            return ret
        return newfunc

    return decorate


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


ROLES = enum('FUEL', 'CONTROLLER', 'COMPUTE', 'CEPH_OSD', 'MONGO', 'UNKNOWN')


class NodeRole(object):
    def __init__(self, role_file_path='/.eayunstack/node-role'):
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

    def is_unknown(self):
        ROLES.UNKNOWN == self.node_role[0]

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
                node_list.append(node['ip'])
            elif node['roles'] == role:
                node_list.append(node['ip'])
    except:
        node_list = []
    return node_list

def ssh_connect(hostname, commands, key_file=os.environ['HOME'] + '/.ssh/id_rsa', ssh_port=22, username='root', timeout=2):
    # Temporarily disable INFO level logging
    logging.disable(logging.INFO)
    # need use rsa key, if use dsa key replace 'RSA' to 'DSS'
    key = paramiko.RSAKey.from_private_key_file(key_file)
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        s.connect(hostname, ssh_port, username=username, pkey=key, timeout=timeout)
        stdin, stdout, stderr = s.exec_command(commands)
        result_out = stdout.read()
        result_err = stderr.read()
    except paramiko.ssh_exception.AuthenticationException:
        result_out = result_err = ''
        LOG.error('Can not connect to this node !')
        LOG.error('Authentication (publickey) failed !')
    except socket.timeout:
        result_out = result_err = ''
        LOG.error('Can not connect to this node !')
        LOG.error('Connect time out !')
    finally:
        s.close()
        logging.disable(logging.NOTSET)
    return result_out, result_err


def ssh_connect2(hostname, commands):
    """exec ssh command and print the result """
    out, err = ssh_connect(hostname, commands)
    if out:
            print out
    elif err:
        print err
    return out, err


def scp_connect(hostname, local_path, remote_path, key_file=os.environ['HOME'] + '/.ssh/id_rsa',username='root', port=22, timeout=2):
    logging.disable(logging.INFO)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        key = paramiko.RSAKey.from_private_key_file(key_file)
        ssh.connect(hostname=hostname, username=username, port=port, pkey=key, timeout=timeout)
        sftp = ssh.open_sftp()
        try:
            sftp.chdir(os.path.dirname(remote_path))
        except IOError:
            sftp.mkdir(os.path.dirname(remote_path))
        sftp.put(local_path,remote_path)
        sftp.close()
    except socket.timeout:
        LOG.error('Can not connect to %s, connection timeout !' % hostname)
    except socket.error:
        LOG.error('Can not connect to %s !' % hostname)
    except paramiko.ssh_exception.AuthenticationException:
        LOG.error('SSH Authentication failed for user %s !' % username)
    except IOError as msg:
        LOG.error('IOError: %s' % msg)
    finally:
        ssh.close()
        logging.disable(logging.NOTSET)
