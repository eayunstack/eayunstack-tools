import logging
import os
import commands
from eayunstack_tools.fuel.db import BACKUP_DIR
from eayunstack_tools.fuel.db import read_db


LOG = logging.getLogger(__name__)


def restore(parser):
    if parser.ID:
        restore_from_id(parser.ID)
    elif parser.FILE:
        restore_from_file(parser.FILE)
    else:
        # FIXME: print help info
        pass


def make(parser):
    '''Fuel Restore'''
    parser.add_argument(
        '-i',
        '--id',
        action='store',
        dest='ID',
        help='Specify the ID you want to restore'
    )
    parser.add_argument(
        '-f',
        '--file',
        action='store',
        dest='FILE',
        help='Specify the backup path to restore'
    )
    parser.set_defaults(func=restore)


def restore_from_id(backup_id):
    LOG.info('Starting restore ...')
    LOG.info('It will take about 30 minutes, Please wait ...\n')
    backups = read_db()
    backup_list = {}
    backup_path = ''
    for line in backups:
        line = line.strip('\n')
        # Put db info into a dictory
        backup_list[line.split(' ')[0]] = line.split(' ')[1]
    if backup_id in backup_list.keys():
        if os.path.isfile(BACKUP_DIR + '/' + backup_list[backup_id]):
            # if is file: backup_path = /var/backup/fuel/{$backup_filename}
            backup_path = BACKUP_DIR + '/' + \
                backup_list[backup_id]
        else:
            # if not file: backup_path = /var/backup/fuel/{$backup_dir}/{$backup_filename}
            # As backup dir has the format: backup_2015-04-09_0831
            # And backup filename: fuel_backup_2015-04-09_0831.tar.lrz
            # backup dir can be known as a part of backup filename
            backup_path = BACKUP_DIR + '/' \
                          + backup_list[backup_id].split('.', 1)[0].split('_', 1)[1] + '/' \
                          + backup_list[backup_id]
        (stat, out) = commands.getstatusoutput('dockerctl restore %s' %
                                               backup_path)
        if stat != 0:
            LOG.error('%s', out)
        else:
            LOG.info('Restore successfully completed!\n')
    else:
        LOG.error('The ID does not exist, Please try again.\n')


def restore_from_file(backup_path):
    LOG.info('Starting Restore ...')
    LOG.info('It will take about 30 minutes, Please wait ...\n')
    (stat, out) = commands.getstatusoutput(
        'dockerctl restore %s' % backup_path)
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Restore successfully completed!\n')
