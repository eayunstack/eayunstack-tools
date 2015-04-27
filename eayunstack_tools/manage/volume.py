#volume management
import logging
import os
import commands
import MySQLdb
import ConfigParser
import re

LOG = logging.getLogger(__name__)

env_path = os.environ['HOME'] + '/openrc'

def volume(parser):
    print "reference module"
    if parser.DESTROY_VOLUME:
        if not parser.ID:
            LOG.error('Please use [--id ID] to specify the volume ID !')
        else:
            volume_id = parser.ID
            global volume_id
            destroy_volume()

def make(parser):
    '''Volume Management'''
    parser.add_argument(
        '-l',
        '--list-errors',
        action='store_const',
        const='list_errors',
        help='List Error Volumes'
    )
    parser.add_argument(
        '-d',
        '--destroy-volume',
        dest='DESTROY_VOLUME',
        action='store_true',
        default=False,
        help='Destroy Volume'
    )
    parser.add_argument(
        '--id',
        action='store',
        dest='ID',
        help='Volume ID'
    )
    parser.set_defaults(func=volume)

def list_errors():
    print "List Error Volume"

def destroy_volume():
    print "Destroy Error Volume: %s" % volume_id
    # get volume's info
    (s, o) = commands.getstatusoutput('source %s && cinder show %s' % (env_path, volume_id))
    if s != 0 or o is None:
        LOG.error('Can not find this volume !')
        return
    else:
        status = get_volume_value(o, 'status')
        volume_type = get_volume_value(o, 'volume_type')
        attachments = get_volume_value(o, 'attachments')

    if not determine_volume_status(status):
        LOG.warn('User give up to destroy this volume.')
        return
    else:
        print 'destroy volume %s' % volume_id
        if not determine_detach_status(attachments):
            LOG.warn('This volume was attached to instance, please delete the instance.')
            return
        else:
            print 'determine snapshots status'
            snapshots_id = get_volume_snapshots()
            if snapshots_id:
                print 'exit or delete all snapshots & volume'
                if not determine_delete_snapshot():
                    LOG.warn('User give up to destroy this volume.')
                    return
                else:
                    # delete all snapshots & volume
                    print 'delete snapshots and volume'
            else:
                print 'delete volume'

def determine_volume_status(status):
    if status in ['available','creating','deleting','error_deleting','attaching','detaching']:
        while True:
            status_determine = raw_input('This volume in "%s" status, do you really want to destroy it? [yes/no]: ' % status)
            if status_determine in ['yes','no']:
                break
        if status_determine == 'yes':
            return True
        else:
            return False
    else:
        return True

def determine_detach_status(attachments):
    if attachments == '[]':
        return True
    else:
        return False

def determine_delete_snapshot():
    while True:
        delete_snapshot = raw_input('This volume has some snapshots , if you want to continue, you must delete the snapshots! Delete the snapshots? [yes/no]: ')
        if delete_snapshot in ['yes','no']:
            break
    if delete_snapshot == 'yes':
        return True
    else:
        return False

def get_volume_snapshots():
    (s, o) = commands.getstatusoutput('source %s && cinder snapshot-list --volume-id %s' % (env_path, volume_id))
    if s != 0 or o is None:
        LOG.error('Can not get the snapshot info for this volume !')
        return
    else:
        snapshots_id = get_snapshots_list(o, volume_id)
    return snapshots_id

def get_snapshots_list(info, key):
    values = []
    for entry in info.split('\n'):
        if len(entry.split('|')) > 1:
            if entry.split('|')[2].strip() == key:
                values.append(entry.split('|')[1].strip())
    return values

def get_volume_value(info, key):
    for entry in info.split('\n'):
        if len(entry.split('|')) > 1:
            if entry.split('|')[1].strip() == key:
                return entry.split('|')[2].strip()

def get_backend_type():
    sql_select_type_id = 'SELECT volume_type_id FROM volumes WHERE id =\'%s\';' % volume_id
    volume_type_id = db_connect(sql_select_type_id)[0]
    sql_select_type_name = 'SELECT name FROM volume_types WHERE id =\'%s\';' % volume_type_id
    backend_type = db_connect(sql_select_type_name)[0]
    return backend_type

def db_connect(sql, user='cinder', dbname='cinder'):
    (host, pwd) = get_db_host_pwd()
    try:
        db = MySQLdb.connect(host, user, pwd, dbname)
        cursor = db.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        db.commit()
        db.close()
        return result
    except:
        LOG.error('Can not connect to database !')

def get_db_host_pwd():
    profile_path = '/etc/cinder/cinder.conf'
    try:
        cp = ConfigParser.ConfigParser()
        cp.read(profile_path)
        value = cp.get('database', 'connection')
        p = re.compile(r'mysql://(.+):(.+)@(.+)/(.+)\?(.+)')
        m = p.match(value).groups()
        # m[2] ==> host m[1] ==> pwd
        return m[2], m[1]
    except:
        LOG.error('Can not get the host address and password for cinder database !')
