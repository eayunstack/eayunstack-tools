import logging
import os
import commands
from utils import BACKUP_DIR
from utils import read_db


LOG = logging.getLogger(__name__)

def restore(parser):
    if parser.ID:
        restore_bck(parser.ID)
    elif parser.FILE:
        restore_file(parser.FILE)
    else:
        parser.help

def make(parser):
    '''Fuel Restore'''
    parser.add_argument(
        '-i',
        '--id',
        action = 'store',
        dest = 'ID',
        type = int,
        help = 'Specify the ID you want to restore'
    )   
    parser.add_argument(
        '-f',
        '--file',
        action = 'store',
        dest = 'FILE',
        help = 'Specify the backup path to restore'
    )   
    parser.set_defaults(func=restore)


def restore_id(id):
    LOG.info('Starting Restore ...')
    LOG.info('It will take about 30 minutes, Please wait ...\n')
    backups = read_db()
    backup_list = {}
    backup_path = ''
    for line in backups:
        line = line.strip('\n')
        # Put db info into a dictory
        backup_list[line.split(' ')[0]] = line.split(' ')[1]
    if id in backup_list.keys():
        if os.path.isfile(BACKUP_DIR + '/' + backup_list[id]):
            backup_path = BACKUP_DIR + '/' \
                          + backup_list[id]
        else:
            backup_path = BACKUP_DIR + '/' \
                          + backup_list[id].split('.', 1)[0].split('_', 1)[1] + '/' \
                          + backup_list[id]
        (stat, out) = commands.getstatusoutput('dockerctl restore %s' % backup_path)
        if stat != 0:
            LOG.error('%s', out)
        else:
            LOG.info('Restore successfully completed!\n')
    else:
        LOG.error('The ID does not exist, Please try again.\n')


def restore_file(backup_path):
    LOG.info('Starting Restore ...')
    LOG.info('It will take about 30 minutes, Please wait ...\n')
    (stat, out) = commands.getstatusoutput('dockerctl restore %s' % backup_path)
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Restore successfully completed!\n')

