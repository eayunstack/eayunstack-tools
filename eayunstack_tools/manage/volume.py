#volume management
import logging
import os
import commands
import MySQLdb
import ConfigParser
import re
import time
from eayunstack_tools.manage.eqlx_ssh_conn import ssh_execute as eqlx_ssh_execute
from eayunstack_tools.sys_utils import ssh_connect
from eayunstack_tools.utils import NODE_ROLE
from eayunstack_tools.manage.utils import get_value as get_volume_value

from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.pythonclient import PythonClient
from eayunstack_tools.stack_db import Stack_DB

env_path = os.environ['HOME'] + '/openrc'

pc = PythonClient()

cinder_db = Stack_DB('cinder')
nova_db = Stack_DB('nova')

def volume(parser):
    if not NODE_ROLE.is_controller():
        LOG.warn('This command can only run on controller node !')
        return
    if parser.DESTROY_VOLUME:
        if not parser.ID:
            LOG.error('Please use [--id ID] to specify the volume ID !')
        else:
            volume_id = parser.ID
            destroy_volume(volume_id)

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

def destroy_volume(volume_id, interactive=True):
    # get volume's info
    volume_info = get_volume_info(volume_id)
    status = volume_info.status
    volume_type = volume_info.volume_type
    attachments = volume_info.attachments
    attached_servers = []
    for attachment in attachments:
        attached_servers.append(attachment['server_id'])

    if interactive and not determine_volume_status(status):
        LOG.warn('User give up to destroy this volume.')
        return
    else:
        if not determine_detach_status(attachments):
            if determine_detach_volume(attached_servers, interactive):
                if detach_volume(attached_servers, volume_id, interactive):
                    snapshots_id = get_volume_snapshots(volume_id)
                    if snapshots_id:
                        if interactive and not determine_delete_snapshot():
                            LOG.warn('User give up to destroy this volume.')
                            return
                        else:
                            # delete all snapshots & volume
                            if delete_snapshots(snapshots_id, volume_id):
                                delete_volume(volume_id, status)
                    else:
                        delete_volume(volume_id, status)
            else:
                LOG.warn('User give up to detach and destroy this volume.')
                return
        else:
            snapshots_id = get_volume_snapshots(volume_id)
            if snapshots_id:
                if interactive and not determine_delete_snapshot():
                    LOG.warn('User give up to destroy this volume.')
                    return
                else:
                    # delete all snapshots & volume
                    if delete_snapshots(snapshots_id, volume_id):
                        delete_volume(volume_id, status)
            else:
                delete_volume(volume_id, status)

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
    if len(attachments) == 0:
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

def get_volume_snapshots(volume_id):
    snapshot_ids = []
    for snapshot in get_snapshot_list(volume_id):
        snapshot_ids.append(snapshot.id)
    return snapshot_ids

def get_backend_type(volume_id):
    backend_type = None
    sql_select_volume_type_name = \
        'select name from volumes,volume_types where \
         volumes.id=\'%s\' and volumes.volume_type_id=volume_types.id' \
         % volume_id
    volume_type_name = db_connect(sql_select_volume_type_name)
    if 'rbd' or 'ceph' in volume_type_name[0]:
        backend_type = 'rbd'
    elif 'eqlx' in volume_type_name[0]:
        backend_type = 'eqlx'
    # TODO the default volume type is "rbd" in eayunstack environment
    if backend_type == None:
        backend_type = 'rbd'
    return backend_type

def get_backend_pool(volume_id):
    volume_info = get_volume_info(volume_id)
    # vol_host_attr like "cinder@cinder_ceph#cinder_ceph"
    vol_host_attr = volume_info._info['os-vol-host-attr:host']

    p = re.compile(r'(.+)@(.+)#(.+)')
    m = p.match(vol_host_attr).groups()
    backend_name = m[1]

    backend_pool = get_config(backend_name, 'rbd_pool')

    return backend_pool


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

def delete_snapshots(snapshots_id, volume_id):
    LOG.info('Deleting snapshot %s ...' % snapshots_id)
    if delete_backend_snapshots(snapshots_id, volume_id):
        try:
            delete_image(snapshots_id)
        except Exception,ex:
            LOG.error('   Delete image failed!\n %s' % ex)
        update_snapshots_db(snapshots_id, volume_id)
        return True
    else:
        return False

def delete_backend_snapshots(snapshots_id, volume_id):
    backend_type = get_backend_type(volume_id)
    if backend_type == 'eqlx':
        if delete_backend_snapshots_eqlx(snapshots_id, volume_id):
            return True
        else:
            return False
    elif backend_type == 'rbd':
        if delete_backend_snapshots_rbd(snapshots_id, volume_id):
            return True
        else:
            return False
    else:
        LOG.error('Do not support to delete "%s" type snapshot.' % backend_type)
        return False

def delete_backend_snapshots_eqlx(snapshots_id, volume_id):
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

def delete_backend_snapshots_rbd(snapshots_id, volume_id):
    success = True
    rbd_pool = get_backend_pool(volume_id)
    LOG.info('   Deleting backend(rbd) snapshots ...')
    for snapshot_id in snapshots_id:
        LOG.info('   [%s]Deleting backend snapshot ...' % snapshot_id)
        (s, o) = commands.getstatusoutput(
                 'rbd -p %s snap unprotect --image volume-%s --snap snapshot-%s'
                 % (rbd_pool, volume_id, snapshot_id))
        if s == 0:
            (ss, oo) = commands.getstatusoutput(
                       'rbd -p %s snap rm --image volume-%s --snap snapshot-%s'
                       % (rbd_pool, volume_id, snapshot_id))
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

def delete_volume(volume_id, volume_status):
    LOG.info('Deleting volume %s ...' % volume_id)
    if volume_status == 'creating':
        update_db(volume_id)
    else:
        if delete_backend_volume(volume_id):
            update_db(volume_id)

def delete_backend_volume(volume_id):
    # get backend store type
    backend_type = get_backend_type(volume_id)
    if backend_type == 'eqlx':
        if delete_backend_volume_eqlx(volume_id):
            return True
        else:
            return False
    elif backend_type == 'rbd':
        if delete_backend_volume_rbd(volume_id):
            return True
        else:
            return False
    else:
        LOG.error('Do not support to delete "%s" type volume.' % backend_type)

def delete_backend_volume_eqlx(volume_id):
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

def delete_backend_volume_rbd(volume_id):
    LOG.info('   Deleting backend(rbd) volume ...')
    rbd_pool = get_backend_pool(volume_id)
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

def update_snapshots_db(snapshots_id, volume_id):
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
            update_snapshot_quota(snapshot_id, volume_id)
        else:
            LOG.error('   Database update faild !')

def update_snapshot_quota(snapshot_id, volume_id):
    # get snapshot size & project id
    sql_get_size_project_id = 'SELECT volume_size,project_id FROM snapshots WHERE id=\'%s\';' % snapshot_id
    get_size_project_id = db_connect(sql_get_size_project_id)
    size = get_size_project_id[0]
    project_id = get_size_project_id[1]
    backend_type = get_backend_type(volume_id)
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
    
def update_db(volume_id):
    LOG.info('   Updating database ...')
    update_volume_table(volume_id)
    update_volume_quota(volume_id)

def update_volume_table(volume_id):
    LOG.info('   [%s]Updating volumes table ...' % volume_id)
    sql_update = 'UPDATE volumes SET deleted=1,status=\'deleted\' WHERE id=\'%s\';' % volume_id
    db_connect(sql_update)
    sql_select = 'SELECT deleted,status FROM volumes WHERE id =\'%s\';' % volume_id
    rest = db_connect(sql_select)
    if rest[0] != 1 or rest[1] != 'deleted':
        LOG.error('   Database update faild !')

def update_volume_quota(volume_id):
    LOG.info('   [%s]Updating volume quota ...' % volume_id)
    # get volume size & project id
    sql_get_size_project_id = 'SELECT size,project_id FROM volumes WHERE id=\'%s\';' % volume_id
    get_size_project_id = db_connect(sql_get_size_project_id)
    size = get_size_project_id[0]
    project_id = get_size_project_id[1]
    # get backend type
    backend_type = get_backend_type(volume_id)
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

def get_volume_info(volume_id):
    logging.disable(logging.INFO)
    volume_info = pc.cinder_get_volume(volume_id)
    logging.disable(logging.NOTSET)
    return volume_info

def get_snapshot_list(volume_id):
    logging.disable(logging.INFO)
    snapshot_list = pc.cinder_get_snapshots(volume_id)
    logging.disable(logging.NOTSET)
    return snapshot_list

def determine_detach_volume(attached_servers, interactive):
    if not interactive:
        return True
    while True:
        detach_volume = raw_input('This volume was attached to instance %s, do you want to detach it and destroy it? [yes/no]: ' % attached_servers)
        if detach_volume in ['yes','no']:
            break
    if detach_volume == 'yes':
        return True
    else:
        return False

def detach_volume(attached_servers, volume_id, interactive):
    LOG.info('Detaching volume "%s" .' % volume_id)
    # check instance was deleted
    exist_servers = []
    for attached_server in attached_servers:
        sql_get_instance_deleted_status = \
            'SELECT deleted from instances where uuid=\'%s\';' \
            %  attached_server
        instance_deleted_status = \
            nova_db.connect(sql_get_instance_deleted_status)[0][0]
        if instance_deleted_status != 0:
            continue
        else:
            exist_servers.append(attached_server)
    if len(exist_servers) == 0:
        # if instance was deleted, set volume attach_status to detached
        if determine_set_volume_to_detached(attached_servers, interactive):
            LOG.info('Set volume %s attach status to detached' % volume_id)
            db_set_volume_detached(volume_id)
            return True
        else:
            LOG.warn('Please set volume attach status to "detached" first.')
            return False
    if detach_disk_on_compute_node(exist_servers, volume_id):
        # update database
        LOG.info('   Updating database.')
        db_set_volume_detached(volume_id)
        for server_id in exist_servers:
            detach_at = time.strftime('%Y-%m-%d %X', time.gmtime())
            sql_update_nova_db = 'UPDATE block_device_mapping SET '\
                                 'deleted_at="%s",deleted=id WHERE '\
                                 'instance_uuid="%s" and volume_id="%s" '\
                                 'and deleted=0;'\
                                 % (detach_at, server_id, volume_id)
            nova_db.connect(sql_update_nova_db)
        return True
    else:
        LOG.warn('Please delete instance "%s" first.' % exist_servers)
        return False

def determine_set_volume_to_detached(attached_servers, interactive):
    if not interactive:
        return True
    while True:
        determine = raw_input('This volume was attached to instances %s, '
                              'but these servers has been deleted, do you '
                              'want to set the volume attach status to '
                              'detached? [yes/no]: ' % attached_servers)
        if determine in ['yes','no']:
            break
    if determine == 'yes':
        return True
    else:
        return False

def db_set_volume_detached(volume_id):
    sql_update_volume_attach_status = 'UPDATE volumes SET status="available",'\
                                      'attach_status="detached" WHERE id="%s";'\
                                      % volume_id
    cinder_db.connect(sql_update_volume_attach_status)
                                      
def detach_disk_on_compute_node(servers, volume_id):
    for server_id in servers:
        LOG.info('   Detaching disk "%s" from instance "%s".' % (volume_id, server_id))
        logging.disable(logging.INFO)
        server = pc.nova_server(server_id)
        server_status = server._info['status']
        server_host = server._info['OS-EXT-SRV-ATTR:host']
        server_instance_name = server._info['OS-EXT-SRV-ATTR:instance_name']
        server_device = os.path.basename(pc.nova_volume(server_id, volume_id)._info['device'])
        logging.disable(logging.NOTSET)
        if disk_attached(server_host, server_instance_name, server_device):
            if server_status == 'ACTIVE':
                detach_disk_cmd = 'virsh detach-disk %s %s --persistent' \
                                  % (server_instance_name, server_device)
                reval = ssh_connect(server_host, detach_disk_cmd)
                if 'Disk detached successfully\n\n' in reval:
                    LOG.info('   Detach disk %s on instance %s successfully.' \
                              % (server_device, server_instance_name))
                    return True
                else:
                    LOG.error('   Detach disk %s on instance %s failed.' \
                              % (server_device, server_instance_name))
                    return False
        else:
            LOG.info('   Disk %s already detached from instance %s.' \
                     % (server_device, server_instance_name))
            return True

def disk_attached(server_host, instance_name, server_device):
    check_cmd = 'virsh domblklist %s | grep -q %s ; echo $?' % (instance_name,
                                                     server_device)
    reval = ssh_connect(server_host, check_cmd)
    if '0\n' in reval:
        return True
    else:
        return False


def delete_image(snapshots_id):
    logging.disable(logging.DEBUG)
    for snapshot_id in snapshots_id:
        tenant_id = pc.cinder_get_tenant_id(snapshot_id)
        images = pc.glance_get_images(tenant_id)
        for image in images:
            image_id = image.get('id')
            image_block_device_mapping = image.get('block_device_mapping')
            if image_block_device_mapping and snapshot_id in image_block_device_mapping:
                LOG.info('   Delete image "%s".' % image_id)
                pc.glance_delete_image(image_id)
    logging.disable(logging.NOTSET)
