# @file backup.py
from eayunstack_tools.fuel.utils import list_backup, latest_backup
from eayunstack_tools.fuel.utils import read_db, write_db
import commands
import logging

# Use the default DIR to backup

LOG = logging.getLogger(__name__)


def backup(parser):
    if parser.NEW_BACKUP:
        new_backup()
    elif parser.LIST_BACKUP:
        list_bck()
    else:
        list_bck()

def make(parser):
    '''Fuel Backup'''
    parser.add_argument(
        '-n',
        '--new',
        action='store_true',
        dest='NEW_BACKUP',
        default=False,
        help='Start A New Backup'
    )
    parser.add_argument(
        '-l',
        '--list',
        action='store_true',
        dest='LIST_BACKUP',
        default=False,
        help='List All Backups'
    )
    parser.set_defaults(func=backup)


def new_backup():
    LOG.info('Starting backup ...')
    LOG.info('It will take about 30 minutes, Please wait ...')
    (stat, out) = commands.getstatusoutput('dockerctl backup')
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Backup successfully completed!\n')
        print 'You can use "eayunstack fuel backup [ -l | --list ]" to list your backups\n'
        # 1) read db to get last_id
        lines = read_db()
        backup_id = 1
        backup_file = latest_backup()
        if len(lines) == 0:
            write_db(backup_id, backup_file)
        else:
            # 2) create new id
            backup_id = int(lines[-1].split(' ')[0])
            backup_id += 1
            # 3) write to db
            write_db(backup_id, backup_file)

def list_bck():
    t = list_backup()
    print t.get_string(sortby='ID')


