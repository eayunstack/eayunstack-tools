# @file utils.py
import os
from prettytable import PrettyTable
import logging

LOG = logging.getLogger(__name__)

BACKUP_DIR = '/var/backup/fuel'


def list_backup():
    """List all the backup file"""
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
        c_time = file_split[3].split('.', 1)[0][:2] \
                 + ':' \
                 + file_split[3].split('.', 1)[0][2:]
        t.add_row([i, c_date + ' ' + c_time, backup_file])
        i += 1
    return t


def read_db():
    """Get Lines as List"""
    try:
        with open('/tmp/tools.db', 'r') as db:
            lines = db.readlines()
            return lines
    except Exception as e:
        os.mknod('/tmp/tools.db')
    finally:
        with open('/tmp/tools.db', 'r') as db:
            lines = db.readlines()
            return lines


def latest_backup():
    """Get The Latest Backup File"""
    # The latest backup file means the new backup file
    # Use sorted() method to sort by filename
    backup_dirs = sorted(os.listdir(BACKUP_DIR + '/'))
    not_backup = 'restore'
    if len(backup_dirs) != 0:
        i = 1
        while True:
            if not_backup in backup_dirs[-i]:
                i += 1
            elif os.path.isfile(BACKUP_DIR + '/' + backup_dirs[-i]):
                # FIXME: Did not consider isfile
                i += 1
            else:
                latest_backup = os.listdir(BACKUP_DIR + '/' \
                                + backup_dirs[-i] + '/')[0]
                return latest_backup
                break


def write_db(backup_id):
    # append
    db = open('/tmp/tools.db', 'a')
    backup_file = latest_backup()
    db.writelines('%s' % backup_id + ' ' + '%s\n' % backup_file)
    db.close()


