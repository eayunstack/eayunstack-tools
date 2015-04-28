#volume management
import logging
import os
import commands
import MySQLdb
import ConfigParser
import re
from eayunstack_tools.manage.eqlx_ssh_conn import ssh_execute as eqlx_ssh_execute
from eayunstack_tools.utils import ssh_connect
from eayunstack_tools.utils import NODE_ROLE

LOG = logging.getLogger(__name__)

env_path = os.environ['HOME'] + '/openrc'

def volume(parser):
    if not NODE_ROLE.is_controller():
        LOG.warn('This command can only run on controller node !')
        return
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

def destroy_volume():
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
        if not determine_detach_status(attachments):
            LOG.warn('This volume was attached to instance, please delete the instance.')
            return
        else:
            snapshots_id = get_volume_snapshots()
            if snapshots_id:
                if not determine_delete_snapshot():
                    LOG.warn('User give up to destroy this volume.')
                    return
                else:
                    # delete all snapshots & volume
                    if delete_snapshots(snapshots_id):
                        delete_volume()
            else:
                delete_volume()

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

def get_config(section, key):
    profile = '/etc/cinder/cinder.conf'
    try:
        cp = ConfigParser.ConfigParser()
        cp.read(profile)
        value = cp.get(section, key)
        return value
    except:
        LOG.error('   Can not get %s\'s value !' % key)

def get_node_list(role):
    profile = '/.eayunstack/node-list'
    node_list = []
    if not os.path.exists(profile):
        return
    node_list_file = open(profile)
    try:
        for line in node_list_file:
            if role in line:
                line = line.split(':')[2]
                node_list.append(line)
    finally:
        node_list_file.close()
    return node_list

def delete_snapshots(snapshots_id):
    LOG.info('Deleting snapshot %s ...' % snapshots_id)
    if delete_backend_snapshots(snapshots_id):
        update_snapshots_db(snapshots_id)
        return True
    else:
        return False

def delete_backend_snapshots(snapshots_id):
    backend_type = get_backend_type()
    if backend_type == 'eqlx':
        if delete_backend_snapshots_eqlx(snapshots_id):
            return True
        else:
            return False
    elif backend_type == 'rbd':
        if delete_backend_snapshots_rbd(snapshots_id):
            return True
        else:
            return False
    else:
        LOG.error('Do not support to delete "%s" type snapshot.' % backend_type)
        return False

def delete_backend_snapshots_eqlx(snapshots_id):
    LOG.info('   Deleting backend(eqlx) snapshots ...')
    for snapshot_id in snapshots_id:
        LOG.info('   [%s]Deleting backend snapshot ...' % snapshot_id)
        cmd_delete_snapshot = 'volume select volume-%s snapshot delete snapshot-%s' % (volume_id, snapshot_id)
        result = eqlx_ssh_execute(cmd_delete_snapshot)
        if 'Snapshot deletion succeeded.' not in result:
            LOG.error('   Can not delete snapshot "%s" !' % snapshot_id)
            return False
        else:
            return True

def delete_backend_snapshots_rbd(snapshots_id):
    success = True
    rbd_pool = get_config('cinder_ceph', 'rbd_pool')
    LOG.info('   Deleting backend(rbd) snapshots ...')
    for snapshot_id in snapshots_id:
        LOG.info('   [%s]Deleting backend snapshot ...' % snapshot_id)
        (s, o) = commands.getstatusoutput('rbd -p volumes snap unprotect --image volume-%s --snap snapshot-%s' % (volume_id, snapshot_id))
        if s == 0:
            (ss, oo) = commands.getstatusoutput('rbd -p volumes snap rm --image volume-%s --snap snapshot-%s' % (volume_id, snapshot_id))
            if ss != 0:
                LOG.error('Can not delete backend snapshot "snapshot-%s" !' % snapshot_id)
                success = False
        elif o.find('No such file or directory') > 0:
            LOG.error('   This snapshot does not exist !')
            success = False
        elif o.find('Device or resource busy') > 0:
            LOG.error('   Unprotecting snapshot failed. Device or resource busy !')
            success = False
        else:
            success = False
    return success

def delete_volume():
    LOG.info('Deleting volume %s ...' % volume_id)
    if delete_backend_volume():
        update_db()

def delete_backend_volume():
    # get backend store type
    backend_type = get_backend_type()
    if backend_type == 'eqlx':
        if delete_backend_volume_eqlx():
            return True
        else:
            return False
    elif backend_type == 'rbd':
        if delete_backend_volume_rbd():
            return True
        else:
            return False
    else:
        LOG.error('Do not support to delete "%s" type volume.' % backend_type)

def delete_backend_volume_eqlx():
    # get provider_location
    sql_get_provider_location = 'SELECT provider_location FROM volumes WHERE id =\'%s\';' % volume_id
    provider_location = str(db_connect(sql_get_provider_location)).split()[1]
    # ssh to controller and compute node to delete the iscsi connection
    LOG.info('   Deleting iscsi connection ...')
    controller_list = get_node_list('controller')
    compute_list = get_node_list('compute')
    node_list = controller_list + compute_list
    for node in node_list:
        cmd_show = 'iscsiadm -m session -o show'
        (out, err) = ssh_connect(node, cmd_show)
        if out.find(provider_location) > 0:
            cmd_delete = 'iscsiadm -m node -u -T %s' % provider_location
            (o, e) = ssh_connect(node, cmd_delete)
            if o.find('successful') < 0:
                LOG.error('   Can not delete the iscsi connection "%s" at host %s.' % (provider_location, node))
    # ssh to eqlx to delete the volume
    LOG.info('   Deleting backend(eqlx) volume ...')
    ## set eqlx volume status to offline
    cmd_set_eqlx_volume_offline = 'volume select volume-%s offline' % volume_id
    out = eqlx_ssh_execute(cmd_set_eqlx_volume_offline)
    if len(out) == 3:
        LOG.error('   ' + out[1])
        return False
    ## delete the eqlx volume
    cmd_delete_eqlx_volume = 'volume delete volume-%s' % volume_id
    result = eqlx_ssh_execute(cmd_delete_eqlx_volume)
    if not result or result[1] != 'Volume deletion succeeded.':
        LOG.error('   Delete backend volume faild !')
        return False
    else:
        return True

def delete_backend_volume_rbd():
    LOG.info('   Deleting backend(rbd) volume ...')
    rbd_pool = get_config('cinder_ceph', 'rbd_pool')
    (s, o) = commands.getstatusoutput('rbd -p %s info volume-%s' % (rbd_pool, volume_id))
    if s != 0:
        LOG.error('   Can not get rbd info for volume "%s" !' % volume_id)
        return False
    else:
        (ss, oo) = commands.getstatusoutput('rbd -p %s rm volume-%s' % (rbd_pool, volume_id))
        if ss != 0:
            LOG.error('   Can not delete rbd volume "%s" !' % volume_id)
            return False
        else:
            return True

def update_snapshots_db(snapshots_id):
   # (host, pwd) = get_db_host_pwd()
    LOG.info('   Updating database ...')
    for snapshot_id in snapshots_id:
        LOG.info('   [%s]Updating snapshots table ...' % snapshot_id)
        sql_update = 'UPDATE snapshots SET deleted=1,status=\'deleted\',progress=\'100%%\' WHERE id=\'%s\';' % snapshot_id
        db_connect(sql_update)
        sql_select = 'SELECT deleted,status,progress from snapshots where id =\'%s\';' % snapshot_id
        rest = db_connect(sql_select)
        if rest[0] == 1 and rest[1] == 'deleted' and rest[2] == '100%':
            LOG.info('   [%s]Updating snapshot quota ...' % snapshot_id)
            update_snapshot_quota(snapshot_id)
        else:
            LOG.error('   Database update faild !')

def update_snapshot_quota(snapshot_id):
    # get snapshot size & project id
    sql_get_size_project_id = 'SELECT volume_size,project_id FROM snapshots WHERE id=\'%s\';' % snapshot_id
    get_size_project_id = db_connect(sql_get_size_project_id)
    size = get_size_project_id[0]
    project_id = get_size_project_id[1]
    backend_type = get_backend_type()
    sql_update_gigabytes = 'UPDATE quota_usages SET in_use=in_use-%s where project_id=\'%s\' and resource=\'gigabytes\';' % (size, project_id)
    sql_update_snapshots = 'UPDATE quota_usages SET in_use=in_use-1 where project_id=\'%s\' and resource=\'snapshots\';' %  project_id
    db_connect(sql_update_gigabytes)
    db_connect(sql_update_snapshots)
    if backend_type == 'eqlx':
        sql_update_snapshots_eqlx = 'UPDATE quota_usages SET in_use=in_use-1 where project_id=\'%s\' and resource=\'snapshots_eqlx\';' % (project_id)
        sql_update_gigabytes_eqlx = 'UPDATE quota_usages SET in_use=in_use-%s where project_id=\'%s\' and resource=\'gigabytes_eqlx\';' % (size, project_id)
        db_connect(sql_update_snapshots_eqlx)
        db_connect(sql_update_gigabytes_eqlx)
    if backend_type == 'rbd':
        sql_update_snapshots_rbd = 'UPDATE quota_usages SET in_use=in_use-1 where project_id=\'%s\' and resource=\'snapshots_rbd\';' % (project_id)
        sql_update_gigabytes_rbd = 'UPDATE quota_usages SET in_use=in_use-%s where project_id=\'%s\' and resource=\'gigabytes_rbd\';' % (size, project_id)
        db_connect(sql_update_snapshots_rbd)
        db_connect(sql_update_gigabytes_rbd)
    
def update_db():
    LOG.info('   Updating database ...')
    update_volume_table()
    update_volume_quota()

def update_volume_table():
    LOG.info('   [%s]Updating volumes table ...' % volume_id)
    sql_update = 'UPDATE volumes SET deleted=1,status=\'deleted\' WHERE id=\'%s\';' % volume_id
    db_connect(sql_update)
    sql_select = 'SELECT deleted,status FROM volumes WHERE id =\'%s\';' % volume_id
    rest = db_connect(sql_select)
    if rest[0] != 1 or rest[1] != 'deleted':
        LOG.error('   Database update faild !')

def update_volume_quota():
    LOG.info('   [%s]Updating volume quota ...' % volume_id)
    # get volume size & project id
    sql_get_size_project_id = 'SELECT size,project_id FROM volumes WHERE id=\'%s\';' % volume_id
    get_size_project_id = db_connect(sql_get_size_project_id)
    size = get_size_project_id[0]
    project_id = get_size_project_id[1]
    # get backend type
    backend_type = get_backend_type()
    sql_update_gigabytes = 'UPDATE quota_usages SET in_use=in_use-%s where project_id=\'%s\' and resource=\'gigabytes\';' % (size, project_id)
    sql_update_volumes = 'UPDATE quota_usages SET in_use=in_use-1 where project_id=\'%s\' and resource=\'volumes\';' %  project_id
    db_connect(sql_update_gigabytes)
    db_connect(sql_update_volumes)
    if backend_type == 'eqlx':
        sql_update_gigabytes_eqlx = 'UPDATE quota_usages SET in_use=in_use-%s where project_id=\'%s\' and resource=\'gigabytes_eqlx\';' % (size, project_id)
        sql_update_volumes_eqlx = 'UPDATE quota_usages SET in_use=in_use-1 where project_id=\'%s\' and resource=\'volumes_eqlx\';' %  project_id
        db_connect(sql_update_gigabytes_eqlx)
        db_connect(sql_update_volumes_eqlx)
    elif backend_type == 'rbd':
        sql_update_gigabytes_rbd = 'UPDATE quota_usages SET in_use=in_use-%s where project_id=\'%s\' and resource=\'gigabytes_rbd\';' % (size, project_id)
        sql_update_volumes_rbd = 'UPDATE quota_usages SET in_use=in_use-1 where project_id=\'%s\' and resource=\'volumes_rbd\';' %  project_id
        db_connect(sql_update_gigabytes_rbd)
        db_connect(sql_update_volumes_rbd)

