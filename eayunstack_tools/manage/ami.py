# @filename ami.py
#ami management
import os
import logging
import commands
from eayunstack_tools.utils import NODE_ROLE

LOG = logging.getLogger(__name__)

env_path = os.environ['HOME'] + '/openrc'

def ami(parser):
    # "if controller leave to last"
    if not parser.KERNEL_FILE and not parser.INITRD_FILE and not parser.IMAGE_FILE:
        LOG.error('Lack of arguments, you can use --help to get help infomation\n')
    elif not parser.KERNEL_FILE:
        LOG.error('Please specify the kernel file\n')
    elif not parser.INITRD_FILE:
        LOG.error('Please specify the initrd file\n')
    elif not parser.IMAGE_FILE:
        LOG.error('Please specify the image file\n')
    else:
        print "upload"
        if parser.NAME:
            AMI_image_upload(parser.KERNEL_FILE, parser.INITRD_FILE, parser.IMAGE_FILE, parser.NAME)
        else:
            AMI_image_upload(parser.KERNEL_FILE, parser.INITRD_FILE, parser.IMAGE_FILE, parser.IMAGE_FILE)

def make(parser):
    '''AMI Image Management'''
    parser.add_argument(
        '--kernel-file',
        action='store',
        dest='KERNEL_FILE',
        help='The path of kernel file you want to use'
    )
    parser.add_argument(
        '--initrd-file',
        action='store',
        dest='INITRD_FILE',
        help='The path of initrd file you want to use'
    )
    parser.add_argument(
        '--imange-file',
        action='store',
        dest='IMAGE_FILE',
        help='The path of image file you want to upload'
    )
    parser.add_argument(
        '-n',
        '--name',
        action='store',
        dest='NAME',
        help='The AMI image name'
    )
    parser.set_defaults(func=ami)

def AMI_image_upload(kernel_file, initrd_file, image_file, name):
    '''AMI Image Upload'''
    kernel_id = kernel_file_upload(kernel_file)
    ramdisk_id = initrd_file_upload(initrd_file)
    (stat, out) = commands.getstatusoutput('source %s && glance image-create --name %s --disk-format=ami --container-format=ami --property kernel_id=%s --property ramdisk_id=%s --file %s' % (env_path, name, kernel_id, ramdisk_id, image_file))
    kernel_file_delete(kernel_id)
    initrd_file_delete(ramdisk_id)
    print "AMI image upload"

def kernel_file_upload(kernel_file):
    '''Upload kernel file and get UUID'''
    (stat, out) = commands.getstatusoutput("source %s && glance image-create --name %s --disk-format=aki --container-format=aki --file %s | grep id | awk '{print $4}'" % (env_path, kernel_file, kernel_file))
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Kernel file uploading...\n')
    print "upload kernel file"
    return out

def initrd_file_upload(initrd_file):
    '''Upload initrd file and get UUID'''
    (stat, out) = commands.getstatusoutput("source %s && glance image-create --name %s --disk-format=ari --container-format=ari --file %s | grep id | awk '{print $4}'" % (env_path, initrd_file, initrd_file))
    if stat != 0:
        LOG.error('%s', out)
    else:
        LOG.info('Initrd file uploading...\n')
    print "upload initrd file"
    return out

def kernel_file_delete(uuid):
    '''Delete tmp kernel file'''
    (stat, out) = commands.getstatusoutput('source %s && glance image-delete %s' % (env_path, uuid))
    if stat != 0:
        LOG.error('%s', out)
        LOG.error('Please use "glance image-delete" to delete it. The uuid is %s', uuid)
    else:
        LOG.info('Kernel file deleting...\n')
    print "delete tmp kernel file"

def initrd_file_delete(uuid):
    '''Delelte tmp initrd file'''
    (stat, out) = commands.getstatusoutput('source %s && glance image-delete %s' % (env_path, uuid))
    if stat != 0:
        LOG.error('%s', out)
        LOG.error('Please use "glance image-delete" to delete it. The uuid is %s', uuid)
    else:
        LOG.info('Initrd file deleting...\n')
    print "delete tmp initrd file"

