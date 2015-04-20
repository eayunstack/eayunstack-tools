# @file backup.py
from eayunstack_tools.fuel.db import latest_backup
from eayunstack_tools.fuel.db import read_db, write_db, check_db
from prettytable import PrettyTable
import commands
import logging

# Use the default DIR to backup

LOG = logging.getLogger(__name__)


def backup(parser):
    if parser.NEW_BACKUP:
        backup_new()
    elif parser.LIST_BACKUP:
        backup_list()
    else:
        backup_list()


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


def backup_new():
    LOG.info('Starting backup ...')
    LOG.info('It will take about 30 minutes, Please wait ...')
    (stat, out) = commands.getstatusoutput('dockerctl backup')
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Backup successfully completed!\n')
        print 'You can use "eayunstack fuel backup [ -l | --list ]" to '\
            'list your backups\n'
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


def list_backup():
    """List all the backup file"""
    # check db before list backup
    check_list = check_db()
    if check_list == 1:
        pass
    else:
        try:
            # TODO: db is not used?
            with open('/tmp/tools.db', 'w') as db:
                for backup_id in check_list.keys():
                    write_db(backup_id, check_list[backup_id])
        except Exception:
            LOG.error('Write to db error!')
    lines = read_db()
    i = 1
    t = PrettyTable(['ID', 'Backup Time', 'Backup File'])
    for line in lines:
        # Delete the '\n' at the end of the line
        # line = 'id backup_file_name\n'
        # e.g. '1 fuel_backup_2015-04-09_0831.tar.lrz'
        line = line.strip('\n')
        backup_id = line.split(' ')[0]
        # backup_file = fuel_backup_2015-04-09_0831.tar.lrz
        backup_file = line.split(' ')[1]
        # file_split = ['fuel', 'backup', '2015-04-09', '0831.tar.lrz']
        file_split = backup_file.split('_', 4)
        # Get the backup time from filename
        # c_date = '2015=04-09'
        c_date = file_split[2]
        # c_time = '08:31'
        c_time = file_split[3].split('.', 1)[0][:2] + ':' + \
            file_split[3].split('.', 1)[0][2:]
        t.add_row([backup_id, c_date + ' ' + c_time, backup_file])
        i += 1
    return t


def backup_list():
    t = list_backup()
    print t.get_string(sortby='ID')
