afrom utils import backup_list
from utils import read_db, write_db
import commands
import logging

# Use the default DIR to backup

LOG = logging.getLogger(__name__)

def backup(parser):
    if parser.NEW_BACKUP:
        new_backup()
    elif parser.LIST_BACKUP:
        list_backup()
    else:
        list_backup()

def make(parser):
    '''Fuel Backup'''
    parser.add_argument(
        '-n',
        '--new',
        action = 'store_true',
        dest = 'NEW_BACKUP',
        default = False,
        help = 'Start A New Backup'
    )   
    parser.add_argument(
        '-l',
        '--list',
        action = 'store_true',
        dest = 'LIST_BACKUP',
        default = False,
        help = 'List All Backups'
    )   
    parser.set_defaults(func=backup)

def new_backup():
    LOG.info('Starting Backup ...')
    LOG.info('It will take about 30 minutes, Please wait ...')
    (stat, out) = commands.getstatusoutput('dockerctl backup')
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Backup successfully completed!\n')
        print 'You can use "eayunstack fuel backup [ -l | --list ]" to list your backups\n'
        # 1) read db to get last_id
        lines = read_db()
        id = 1
        if len(lines) == 0:
            write_db(id)
        else:
            # 2) create new id
            id = int(lines[-1].split(' ')[0])
            id += 1
            # 3) write to db
            write_db(id)

def list_backup():
    t = backup_list()
    print t.get_string(sortby = 'ID')


