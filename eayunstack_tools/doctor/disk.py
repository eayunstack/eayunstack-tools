#check disk space
import os
import math
import logging
from eayunstack_tools.doctor.utils import set_logger

limit = 85

def check_disk(LOG):
    vfs = os.statvfs("/")
    # get "/" filesystem space used percent
    used_percent = int(math.ceil((float(vfs.f_blocks-vfs.f_bavail)/float(vfs.f_blocks))*100))
    if used_percent >= 0 and used_percent < limit:
        LOG.info('The "/" filesystem used %s%% space !' % used_percent)
    elif used_percent >= limit:
        LOG.warn('The "/" filesystem used %s%% space !' % used_percent)
