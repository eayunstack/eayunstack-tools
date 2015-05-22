import logging
import os
import commands
from eayunstack_tools.fuel.db import BACKUP_DIR, BackupDB
from eayunstack_tools.logger import StackLOG as LOG


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
    try:
        db = BackupDB()
        backup_path = db.read(int(backup_id))
        (stat, out) = commands.getstatusoutput('dockerctl restore %s'
                                               % backup_path)
        if stat != 0:
            LOG.error('%s' % out)
        else:
            LOG.info('Restore successfully completed!\n')
    except:
        LOG.error('The ID does not exist, Please try again.\n')


def restore_from_file(backup_path):
    LOG.info('Starting Restore ...')
    LOG.info('Backup is in progress, Please wait ...\n')
    (stat, out) = commands.getstatusoutput(
        'dockerctl restore %s' % backup_path)
    if stat != 0:
        LOG.error('%s' % out)
    else:
        LOG.info('Restore successfully completed!\n')
