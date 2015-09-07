#instance management
import logging
import commands
from eayunstack_tools.sys_utils import ssh_connect
from eayunstack_tools.utils import NODE_ROLE
from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.pythonclient import PythonClient
from eayunstack_tools.stack_db import Stack_DB
from eayunstack_tools.manage.volume import destroy_volume

pc = PythonClient()

nova_db = Stack_DB('nova')
cinder_db = Stack_DB('cinder')

convert = [('hypervisor_hostname', 'OS-EXT-SRV-ATTR:hypervisor_hostname'),
           ('volumes_attached', 'os-extended-volumes:volumes_attached'),
           ('instance_name', 'OS-EXT-SRV-ATTR:instance_name')]

def instance(parser):
    if not NODE_ROLE.is_controller():
        LOG.warn('This command can only run on controller node !')
        return
    if parser.DELETE_INTANCE:
        if not parser.ID:
            LOG.error('Please use [--id ID] to specify the instance ID !')
        else:
            instance_id = parser.ID
            if parser.DELETE_DISK:
                delete_instance(instance_id, delete_disk=True)
            else:
                delete_instance(instance_id)

def make(parser):
    '''Instance Management'''
    parser.add_argument(
        '-d',
        '--delete-instance',
        dest='DELETE_INTANCE',
        action='store_true',
        default=False,
        help='Delete Instance'
    )
    parser.add_argument(
        '--id',
        action='store',
        dest='ID',
        help='Instance ID'
    )
    parser.add_argument(
        '--delete-disk',
        action='store_true',
        dest='DELETE_DISK',
        default=False,
        help='Delete Instance Disk',
    )
    parser.set_defaults(func=instance)

def delete_instance(instance_id, delete_disk=False):
    if not pc.nova_server_exist(instance_id):
        LOG.error('Instance "%s" is not exist !' % instance_id)
        return
    instance_status = get_instance_status(instance_id)
    if determine_delete_instance(instance_id, instance_status):
        LOG.info('Delete instance "%s".' % instance_id)
        instance_power_state = get_instance_power_state(instance_id)
        if instance_power_state == 'running':
            LOG.info('Instance "%s" is running, try to destroy it.' % instance_id)
            if destroy_instance(instance_id):
                delete_vnic_vbr(instance_id)
                delete_instance_dir(instance_id)
                undefine_instance(instance_id)
                delete_ports(instance_id)
                update_disk_state(instance_id)
                if delete_disk:
                    delete_disks(instance_id)
                update_nova_db(instance_id)
        else:
            delete_vnic_vbr(instance_id)
            delete_instance_dir(instance_id)
            undefine_instance(instance_id)
            delete_ports(instance_id)
            update_disk_state(instance_id)
            if delete_disk:
                delete_disks(instance_id)
            update_nova_db(instance_id)

def get_instance_status(instance_id):
    instance_status = get_instance_info(instance_id, 'status')
    return instance_status

def get_hypervisor_hostname(instance_id):
    hypervisor_hostname = get_instance_info(instance_id, 'hypervisor_hostname')
    return hypervisor_hostname

def get_instance_name(instance_id):
    instance_name = get_instance_info(instance_id, 'instance_name')
    return instance_name

def get_tenant_id(instance_id):
    tenant_id = get_instance_info(instance_id, 'tenant_id')
    return tenant_id

def get_flavor(instance_id):
    flavor = get_instance_info(instance_id, 'flavor')
    return flavor

def get_flavor_resource(flavor_id, key):
    logging.disable(logging.INFO)
    flavor = pc.nova_flavor(flavor_id)
    value = flavor._info[key]
    logging.disable(logging.NOTSET)
    return value

def get_volumes_attached(instance_id):
    volumes = get_instance_info(instance_id, 'volumes_attached')
    return volumes

def get_instance_info(instance_id, key):
    logging.disable(logging.INFO)
    server = pc.nova_server(instance_id)
    key = _translate_key(key, convert)
    value = server._info[key]
    logging.disable(logging.NOTSET)
    return value

# get instance state from compute node
def get_instance_power_state(instance_id):
    compute_node = get_hypervisor_hostname(instance_id)
    instance_name = get_instance_name(instance_id)
    cmd = 'virsh domstate %s' % instance_name
    instance_state = ssh_connect(compute_node, cmd)[0].split('\n')[0]
    return instance_state

# get instance interface list
def get_interface_list(instance_id):
    logging.disable(logging.INFO)
    server = pc.nova_server(instance_id)
    interface_list = server.interface_list()
    logging.disable(logging.NOTSET)
    return interface_list

def determine_delete_instance(instance_id, instance_state):
    if instance_state != 'ERROR':
        LOG.warn('Instance is not in "ERROR" status. Can not delete it!')
        return False
    else:
        while True:
            determine = raw_input('Instance "%s" is in "ERROR" status. Do you really want to delete it? [yes/no]: ' % instance_id)
            if determine in ['yes','no']:
                break
        if determine == 'yes':
            return True
        else:
            return False

# destroy instance on compute node
def destroy_instance(instance_id):
    compute_node = get_hypervisor_hostname(instance_id)
    instance_name = get_instance_name(instance_id)
    cmd = 'virsh destroy %s' % instance_name
    LOG.info('Destroy instance "%s".' % instance_id)
    reval = ssh_cmd(compute_node, cmd)
    if 'Domain %s destroyed' % instance_name in reval:
        LOG.info('Destroy instance "%s" successfully.' % instance_id)
        return True
    else:
        LOG.info('Destroy instance "%s" failed.' % instance_id)
        return False

def get_devid(instance_id):
    interface_list = get_interface_list(instance_id)
    devid = []
    for interface in interface_list:
        devid.append(interface.port_id[0:11])
    return devid

def delete_vnic_vbr(instance_id):
    compute_node = get_hypervisor_hostname(instance_id)
    dev_ids = get_devid(instance_id)
    for dev_id in dev_ids:
        # device name
        tap = 'tap' + dev_id
        qbr = 'qbr' + dev_id
        qvb = 'qvb' + dev_id
        qvo = 'qvo' + dev_id
        del_if_cmd = 'brctl delif %s %s; echo $?' % (qbr, qvb) # TODO determine use qvb or tap
        set_if_down_cmd = 'ip link set %s down; echo $?' % qbr
        delbr_cmd = 'brctl delbr %s; echo $?' % qbr
        del_ovsport_cmd = 'ovs-vsctl --if-exists del-port br-int %s; echo $?' % qvo
        if ssh_cmd(compute_node, del_if_cmd) == '0':
            LOG.info('Delete interface "%s" from bridge "%s" successfully.' % (qbr, qvb))
            if ssh_cmd(compute_node, set_if_down_cmd) == '0':
                LOG.info('Set nic "%s" state to down successfully.' % qbr)
                if ssh_cmd(compute_node, delbr_cmd) == '0':
                    LOG.info('Delete bridge "%s" successfully.' % qbr)
                    if ssh_cmd(compute_node, del_ovsport_cmd) == '0':
                        LOG.info('Delete ovs port "%s" successfully.' % qvo)
                    else:
                        LOG.error('Delete ovs port "%s" failed.' % qvo)
                else:
                    LOG.error('Delete bridge "%s" failed.' % qbr)
            else:
                LOG.error('Set nic "%s" state to down failed.' % qbr)
        else:
            LOG.error('Delete interface "%s" from bridge "%s" failed.' % (qbr, qvb))

def delete_instance_dir(instance_id):
    compute_node = get_hypervisor_hostname(instance_id)
    LOG.info('Delete instance dir on compute node "%s".' % compute_node)
    rm_basic_dir_cmd = 'rm -rf /var/lib/nova/instances/%s' % instance_id
    rm_resize_dir_cmd = 'rm -rf /var/lib/nova/instances/%s_resize' % instance_id
    rm_del_dir_cmd = 'rm -rf /var/lib/nova/instances/%s_del' % instance_id
    ssh_cmd(compute_node, rm_basic_dir_cmd)
    ssh_cmd(compute_node, rm_resize_dir_cmd)
    ssh_cmd(compute_node, rm_del_dir_cmd)

def undefine_instance(instance_id):
    compute_node = get_hypervisor_hostname(instance_id)
    instance_name = get_instance_name(instance_id)
    LOG.info('Undefine instance on compute node "%s".' % compute_node)
    undefine_cmd = 'virsh undefine %s' % instance_name
    ssh_cmd(compute_node, undefine_cmd)

def delete_ports(instance_id):
    interface_list = get_interface_list(instance_id)
    for interface in interface_list:
        port_id = interface.port_id
        delete_port(port_id)

def delete_port(port_id):
    LOG.info('Delete port "%s".' % port_id)
    logging.disable(logging.INFO)
    pc.neutron_delete_port(port_id)
    logging.disable(logging.NOTSET)

def update_disk_state(instance_id):
    volumes = get_volumes_attached(instance_id)
    for volume in volumes:
        volume_id = volume['id']
        set_volume_to_available(volume_id)

def set_volume_to_available(volume_id):
    LOG.info('Set disk "%s" state to available.' % volume_id)
    sql_update_cinder_db = 'UPDATE volumes SET status="available",attach_status="detached" WHERE id="%s";' % volume_id
    cinder_db.connect(sql_update_cinder_db)

def delete_disks(instance_id):
    volumes = get_volumes_attached(instance_id)
    for volume in volumes:
        volume_id = volume['id']
        delete_disk(volume_id)

def delete_disk(volume_id):
    LOG.info('Delete disk "%s".' % volume_id)
    destroy_volume(volume_id)

def update_nova_db(instance_id): 
    LOG.info('Update nova database.')
    tenant_id = get_tenant_id(instance_id)
    flavor_id = get_flavor(instance_id)['id']
    ram_usage = get_flavor_resource(flavor_id, 'ram')
    vcpu_usage = get_flavor_resource(flavor_id, 'vcpus')
    # update instances table vm_state power_state
    nova_db.connect('UPDATE instances SET vm_state="deleted",power_state=0,deleted=id WHERE uuid="%s";' % instance_id)
    # update quota_usages table instances
    nova_db.connect('UPDATE quota_usages SET in_use=in_use-1 WHERE project_id="%s" and resource="instances";' % tenant_id)
    # update quota_usages table
    nova_db.connect('UPDATE quota_usages SET in_use=in_use-%s WHERE project_id="%s" and resource="ram";' % (ram_usage, tenant_id))
    # update quota_usages table
    nova_db.connect('UPDATE quota_usages SET in_use=in_use-%s WHERE project_id="%s" and resource="cores";' % (vcpu_usage, tenant_id))
    # update instance_faults table
    nova_db.connect('UPDATE instance_faults SET deleted=id WHERE instance_uuid="%s";' % instance_id)
    # update instance_info_caches table
    nova_db.connect('UPDATE instance_info_caches SET deleted=id WHERE instance_uuid="%s";' % instance_id)
    # update security_group_instance_association table
    nova_db.connect('UPDATE security_group_instance_association SET deleted=id WHERE instance_uuid="%s";' % instance_id)
    # update block_device_mapping table
    nova_db.connect('UPDATE block_device_mapping SET deleted=id WHERE instance_uuid="%s";' % instance_id)
    # update fixed_ips table
    nova_db.connect('UPDATE fixed_ips SET deleted=id WHERE instance_uuid="%s";' % instance_id)
    # update virtual_interfaces table
    nova_db.connect('UPDATE virtual_interfaces SET deleted=id WHERE instance_uuid="%s";' % instance_id)

def _translate_key(key, convert):
    for from_key, to_key in convert:
        if from_key == key:
            key = to_key
    return key

# run command on remote host by ssh
def ssh_cmd(hostname, cmd):
    reval = ssh_connect(hostname, cmd)[0].split('\n')[0]
    return reval

