# @filename ami.py
# ami management

import os
import logging
import commands

from eayunstack_tools.manage.utils import get_value
from eayunstack_tools.utils import NODE_ROLE
from eayunstack_tools.logger import StackLOG as LOG


env_path = os.environ['HOME'] + '/openrc'


def ami(parser):
    if not NODE_ROLE.is_controller():
        LOG.warn('This command can only run on controller node !')
    else:
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
            if parser.NAME:
                # split the path and filename
                kernel_file_name = os.path.basename(r'%s' % parser.KERNEL_FILE)
                initrd_file_name = os.path.basename(r'%s' % parser.INITRD_FILE)
                ami_image_upload(parser.KERNEL_FILE, kernel_file_name,
                                 parser.INITRD_FILE, initrd_file_name,
                                 parser.IMAGE_FILE, parser.NAME)
            else:
                # if not specify image name, use IMAGE_FILE as AMI name
                # split the path and filename
                kernel_file_name = os.path.basename(r'%s' % parser.KERNEL_FILE)
                initrd_file_name = os.path.basename(r'%s' % parser.INITRD_FILE)
                ami_image_name = os.path.basename(r'%s' % parser.IMAGE_FILE)
                ami_image_upload(parser.KERNEL_FILE, kernel_file_name,
                                 parser.INITRD_FILE, initrd_file_name,
                                 parser.IMAGE_FILE, ami_image_name)

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
        '--image-file',
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

def ami_image_upload(kernel_file, kernel_file_name,
                     initrd_file, initrd_file_name,
                     image_file, name):
    '''AMI Image Upload'''
    kernel_id = kernel_file_upload(kernel_file, kernel_file_name)
    ramdisk_id = initrd_file_upload(initrd_file, initrd_file_name)
    # if kernel file upload successfully but initrd file failed:
    if not kernel_id:
        # if both failed:
        if not ramdisk_id:
            LOG.error('AMI image upload failed, please try again.\n')
        else:
            LOG.error('AMI image upload failed because of the failed of kernel file. Please try again.\n')
            # delete the successful initrd image
            delete_image(ramdisk_id)
    # if initrd file upload successfully but kernel file failed:
    elif not ramdisk_id:
        # if both failed:
        if not kernel_id:
            LOG.error('AMI image upload failed, please try again.\n')
        else:
            LOG.error('AMI image upload failed because of the failed of initrd file. Please try again.\n')
            # delete the successful kernel image
            delete_image(kernel_id)
    else:
        LOG.info('AMI image uploading...\n')
        (stat, out) = commands.getstatusoutput('source %s && glance image-create --name %s --disk-format=ami --container-format=ami --property kernel_id=%s --property ramdisk_id=%s --file %s --is-public True'
                                               % (env_path, name, kernel_id, ramdisk_id, image_file))
        if stat != 0:
            LOG.error('%s' % out)
            # if AMI image upload failed, delete kernel image and initrd image:
            delete_image(kernel_id)
            delete_image(ramdisk_id)
        else:
            LOG.info('AMI image upload successfully!\n')
            print out
            # if successfully, cannot delete,
            # protect the kernel image and initrd image.
            protect_image(kernel_id)
            protect_image(ramdisk_id)

def kernel_file_upload(kernel_file, name):
    '''Upload kernel file and get UUID'''
    LOG.info('Kernel file uploading...\n')
    (stat, out) = commands.getstatusoutput('source %s && glance image-create --name %s --disk-format=aki --container-format=aki --file %s'
                                           % (env_path, name, kernel_file))
    if stat != 0:
        LOG.error('Kernel file upload failed.')
        LOG.error('%s\n' % out)
        return 0
    else:
        LOG.info('Kernel file upload successfully.\n')
        # if successfully, git kernel_id
        kernel_id = get_value(out, "id")
        return kernel_id

def initrd_file_upload(initrd_file, name):
    '''Upload initrd file and get UUID'''
    LOG.info('Initrd file uploading...\n')
    (stat, out) = commands.getstatusoutput('source %s && glance image-create --name %s --disk-format=ari --container-format=ari --file %s'
                                           % (env_path, name, initrd_file))
    if stat != 0:
        LOG.error('Initrd file upload failed.')
        LOG.error('%s\n' % out)
        return 0
    else:
        LOG.info('Initrd file upload successfully.\n')
        # if successfully, git ramdisk_id
        ramdisk_id = get_value(out, "id")
        return ramdisk_id

def delete_image(uuid):
    '''Delete tmp kernel file'''
    LOG.info('Image deleting...\n')
    (stat, out) = commands.getstatusoutput('source %s && glance image-delete %s'
                                           % (env_path, uuid))
    if stat != 0:
        LOG.error('%s' % out)
        # if delete failed, tell user the uuid and let user delete manually
        LOG.error('Please use "glance image-delete" to delete it. The uuid is %s\n' % uuid)
    else:
        LOG.info('The image was deleted.\n')

def protect_image(uuid):
    '''Protect kernel image and initrd image'''
    LOG.info('Image protecting...')
    (stat, out) = commands.getstatusoutput('source %s && glance image-update --is-protected True %s' % (env_path, uuid))
    if stat != 0:
        LOG.error('%s' % out)
    else:
        LOG.info('Protected successfully.\n')

