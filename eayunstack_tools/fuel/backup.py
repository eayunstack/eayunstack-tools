# @file backup.py
from eayunstack_tools.fuel.db import BackupDB
from prettytable import PrettyTable
import commands
import logging
import os


# Use the default DIR to backup

from eayunstack_tools.logger import StackLOG as LOG


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
        help='Create A New Backup'
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
    # for test
    # import time
    # sec = int(time.time() - 1429595568)
    # os.system('mkdir /var/backup/fuel/backup_2015-04-23_%d' % sec)
    # os.system('touch /var/backup/fuel/backup_2015-04-23_%d/fuel_backup_2015-04-19_%d.tar.lrz' % (sec, sec))
    # (stat, out) = (0, '_')
    (stat, out) = commands.getstatusoutput('dockerctl backup')
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Backup successfully completed!\n')
        print 'You can use "eayunstack fuel backup [ -l | --list ]" to '\
            'list your backups\n'
        db = BackupDB()
        f = db.latest_backupfile()
        db.write(f)


def backup_list():
    t = PrettyTable(['ID', 'Backup Time', 'Backup File'])
    db = BackupDB()
    db_item = db.read_all()
    for backup_id in db_item.keys():
        # backup_file = fuel_backup_2015-04-09_0831.tar.lrz
        backup_file = os.path.basename(db_item[backup_id])
        # file_split = ['fuel', 'backup', '2015-04-09', '0831.tar.lrz']
        file_split = backup_file.split('_', 4)
        # Get the backup time from filename
        # c_date = '2015=04-09'
        c_date = file_split[2]
        # c_time = '08:31'
        c_time = file_split[3].split('.', 1)[0][:2] + ':' + \
            file_split[3].split('.', 1)[0][2:]
        t.add_row([backup_id, c_date + ' ' + c_time, backup_file])
    print t.get_string(sortby='ID')
