# @file utils.py
import os
import logging

LOG = logging.getLogger(__name__)

BACKUP_DIR = '/var/backup/fuel'


def read_db():
    """Get Lines as List"""
    try:
        with open('/tmp/tools.db', 'r') as db:
            lines = db.readlines()
            return lines
    except Exception:
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
                latest_backup = os.listdir(BACKUP_DIR + '/' +
                                           backup_dirs[-i] + '/')[0]
                return latest_backup


def write_db(backup_id, backup_file):
    # append
    try:
        with open('/tmp/tools.db', 'a') as db:
            db.writelines('%s' % backup_id + ' ' + '%s\n' % backup_file)
    except Exception:
        LOG.error('Write to db error!')


def check_db():
    """Check if db sync with /var/backup/fuel"""
    backup_dirs = os.listdir(BACKUP_DIR)
    backup_files = []
    backup_dict = {}
    # Output the backup file under /var/backup/fuel as a list
    for backup_dir in backup_dirs:
        if os.path.isfile(BACKUP_DIR + '/' + backup_dir):
            backup_files.append(backup_dir)
        else:
            # if delete the backup file but didn't delete backup dir,
            # won't write to backup_files
            if os.listdir(BACKUP_DIR + '/' + backup_dir) == []:
                pass
            else:
                backup_files.append(os.listdir(BACKUP_DIR + '/' +
                                               backup_dir)[0])
    list_old = read_db()
    backup_list = read_db()
    print backup_files
    i = 0
    # Compare backup_list and backup_files
    try:
        while True:
            # if tools.db was empty
            if len(backup_list) == 0:
                break
            # if backup_list sync with backup_files, do nothing
            elif backup_list[i].split(' ')[1].strip('\n') in backup_files:
                i += 1
            # if not, means backup_file has been deleted, deleted
            # from backup_list
            else:
                backup_list.remove(backup_list[i])
    except Exception:
        pass
    finally:
        if list_old == backup_list:
            return 1  # true
        else:
            # Output the new backup_list as a dict
            for line in backup_list:
                line = line.strip('\n')
                # backup_dict = {'id': 'backup_file'}
                backup_dict[line.split(' ')[0]] = line.split(' ')[1]
            return backup_dict
