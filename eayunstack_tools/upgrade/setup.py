import os
import commands
import ConfigParser

from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.sys_utils import scp_connect, ssh_connect2
from eayunstack_tools.utils import NODE_ROLE


def setup(parser):
    """Set things up for the upgrade operation."""
    if NODE_ROLE.is_fuel():
        setup_rsyncd_config()
        setup_nodes(parser.MYIP)
    else:
        LOG.error('This command can only be run on the fuel node.')


def make(parser):
    parser.add_argument(
        '--myip',
        action='store',
        dest='MYIP',
        required=True,
        help='IP address of the fuel node'
    )
    parser.set_defaults(func=setup)


def setup_rsyncd_config():
    tmp_rsyncd_conf = '/tmp/rsyncd.conf'
    rsyncd_conf = 'rsync:/etc/rsyncd.conf'
    target_section = 'eayunstack'
    settings = {
        'path': '/var/www/nailgun/eayunstack',
        'read only': 'true',
        'uid': '0',
        'gid': '0',
        'use chroot': 'no',
    }
    docker_copy_command = 'dockerctl copy {src} {dst}'
    copy_out = docker_copy_command.format(src=rsyncd_conf, dst=tmp_rsyncd_conf)
    copy_in = docker_copy_command.format(src=tmp_rsyncd_conf, dst=rsyncd_conf)

    (s, o) = commands.getstatusoutput(copy_out)
    if s != 0:
        LOG.error('Failed to copy the rsyncd configuration out.')
        return

    config = ConfigParser.RawConfigParser()
    config.read(tmp_rsyncd_conf)

    if not config.has_section(target_section):
        config.add_section(target_section)
        for option, value in settings.iteritems():
            config.set(target_section, option, value)

        with open(tmp_rsyncd_conf, 'wb') as configfile:
            config.write(configfile)

        (s, o) = commands.getstatusoutput(copy_in)
        if s != 0:
            LOG.error('Failed to copy the rsyncd configuration in.')

    os.unlink(tmp_rsyncd_conf)


def setup_nodes(myip):
    repo_content = """
[eayunstack]
name=eayunstack
baseurl=http://{ip}:8080/eayunstack/repo
gpgcheck=0
"""
    tmp_repo_file = '/tmp/eayunstack.repo'
    target_repo_file = '/etc/yum.repos.d/eayunstack.repo'
    with open(tmp_repo_file, 'wb') as f:
        f.write(repo_content.format(ip=myip))

    setup_command = 'mkdir -p /var/lib/eayunstack/{upgrade,puppet}'
    for node in NODE_ROLE.nodes:
        scp_connect(node['ip'], tmp_repo_file, target_repo_file)
        ssh_connect2(node['ip'], setup_command)

    os.unlink(tmp_repo_file)
