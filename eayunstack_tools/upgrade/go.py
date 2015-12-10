import os
import commands
import json

from fuelclient.client import APIClient

from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.utils import NODE_ROLE

RUNDIR = '/var/run/eayunstack'
FIRST_CONTROLLER = os.path.join(RUNDIR, 'first_controller')
OTHER_NODES = os.path.join(RUNDIR, 'other_nodes')

MCO_COMMAND_PREFIX = 'dockerctl shell astute mco rpc -j {nodes} '


def go(parser):
    """Upgrade"""
    if NODE_ROLE.is_fuel():
        if parser.CHECK_ONLY:
            check_upgrade_process()
        else:
            go_upgrade(parser.MYIP)
    else:
        LOG.error('This command can only be run on the fuel node.')


def make(parser):
    parser.add_argument(
        '--myip',
        action='store',
        dest="MYIP",
        required=True,
        help='IP address of the fuel node'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        dest='CHECK_ONLY',
        default=False,
        help=('If specified, the program will only check the current progress '
              'instead of start a new upgrade process.')
    )
    parser.set_defaults(func=go)


def check_upgrade_process():
    CHECK_COMMAND = MCO_COMMAND_PREFIX + 'puppetd last_run_summary'
    errors = 0
    runnings = 0

    if os.path.isdir(RUNDIR) and os.path.isfile(FIRST_CONTROLLER):
        to_check = []

        if os.path.isfile(OTHER_NODES):
            file_to_open = OTHER_NODES
        else:
            file_to_open = FIRST_CONTROLLER

        with open(file_to_open, 'r') as nodes_file:
            for line in nodes_file:
                to_check += line.strip().split()

        (s, o) = commands.getstatusoutput(
            CHECK_COMMAND.format(
                nodes=' '.join(['-I %s' % n for n in to_check])))
        if s == 0:
            ret = json.loads(o)
            for node_info in ret:
                sender = node_info['sender']
                data = node_info['data']
                if data['status'] == 'stopped':
                    if data['resources']['failed'] > 0:
                        LOG.error('Error occured on node %s. Check it!' %
                                  sender)
                        errors += 1
                    else:
                        LOG.info('Process on node %s is finished.' % sender)
                        LOG.info(
                            'Events:\n'
                            '    total: {total}\n'
                            '    success: {success}\n'
                            '    failure: {failure}'.format(
                                **data['events']
                            )
                        )
                        LOG.info(
                            'Resources:\n'
                            '    total: {total}\n'
                            '    changed: {changed}\n'
                            '    failed: {failed}\n'
                            '    restarted: {restarted}\n'
                            '    failed_to_restart: {failed_to_restart}\n'
                            '    scheduled: {scheduled}\n'
                            '    skipped: {skipped}\n'
                            '    out_of_sync: {out_of_sync}'.format(
                                **data['resources']
                            )
                        )
                else:
                    LOG.info('Process on node %s is still running.' % sender)
                    runnings += 1
        else:
            LOG.error('Failed to check the current upgrade process.')
            errors += 65535
    else:
        LOG.info('No upgrade process is currently on the way.')

    if errors == 0 and runnings == 0 and os.path.isfile(OTHER_NODES):
        # Mission completed
        os.unlink(FIRST_CONTROLLER)
        os.unlink(OTHER_NODES)
    return errors + runnings


def go_upgrade(myip):
    MODULES_SOURCE = 'rsync://%s:/eayunstack/puppet/modules' % myip
    MANIFESTS_SOURCE = 'rsync://%s:/eayunstack/puppet/manifests' % myip

    CWD = '/var/lib/eayunstack'

    RELATIVE_MODULES_PATH = 'puppet/modules'
    MODULES_PATH = os.path.join(CWD, RELATIVE_MODULES_PATH)
    MANIFESTS_PATH = os.path.join(CWD, 'puppet/manifests')

    MANIFEST = os.path.join(MANIFESTS_PATH, 'site.pp')
    MODULES = ':'.join([RELATIVE_MODULES_PATH, '/etc/puppet/modules'])

    SYNC_COMMAND = ' '.join([MCO_COMMAND_PREFIX, 'puppetsync rsync',
                             'modules_source=%s' % MODULES_SOURCE,
                             'manifests_source=%s' % MANIFESTS_SOURCE,
                             'modules_path=%s' % MODULES_PATH,
                             'manifests_path=%s' % MANIFESTS_PATH])
    RUN_COMMAND = ' '.join([MCO_COMMAND_PREFIX, 'puppetd runonce',
                            'manifest=%s' % MANIFEST,
                            'cwd=%s' % CWD,
                            'modules=%s' % MODULES])

    if not os.path.isdir(RUNDIR):
        os.makedirs(RUNDIR)

    nodes = APIClient.get_request('nodes/')
    if not os.path.isfile(FIRST_CONTROLLER):
        for n in nodes:
            if n['online'] and 'controller' in n['roles']:
                first_controller = str(n['id'])
                break
        with open(FIRST_CONTROLLER, 'wb') as first_controller_file:
            first_controller_file.write(first_controller)
        nodes = [first_controller]
    else:
        current_running = check_upgrade_process()
        if current_running > 0:
            return
        with open(FIRST_CONTROLLER, 'r') as first_controller_file:
            first_controller = first_controller_file.readline()
        nodes = [
            n['id'] for n in nodes
            if n['online'] and n['id'] != first_controller
        ]
        with open(OTHER_NODES, 'wb') as other_nodes_file:
            other_nodes_file.write(' '.join(nodes))

    nodes_in_command = ' '.join(['-I %s' % n for n in nodes])

    errors = 0
    (s, o) = commands.getstatusoutput(
        SYNC_COMMAND.format(nodes=nodes_in_command))
    if s == 0:
        ret = json.loads(o)
        for node_info in ret:
            sender = node_info['sender']
            data = node_info['data']
            if node_info['statuscode'] == 0:
                LOG.info('node %s: %s' % (sender, data['msg']))
            else:
                LOG.error('node %s: %s' % (sender, node_info['statusmsg']))
                errors += 1
    else:
        LOG.error('Failed to sync puppet modules to nodes %s.' % nodes)
        errors += 1

    if errors:
        return

    (s, o) = commands.getstatusoutput(
        RUN_COMMAND.format(nodes=nodes_in_command))
    if s == 0:
        ret = json.loads(o)
        for node_info in ret:
            sender = node_info['sender']
            data = node_info['data']
            if node_info['statuscode'] == 0:
                LOG.info('node %s: %s' % (sender, data['output']))
            else:
                LOG.error('node %s: %s' % (sender, data['output']))
    else:
        LOG.error('Failed to run puppet on nodes %s.' % nodes)
