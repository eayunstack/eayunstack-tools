#check selinux status
import logging
import commands
import re
from eayunstack_tools.doctor.utils import set_logger

# Correct state [enforcing, permissive, disabled]
correct_state = correct_conf = "disabled"

def check_selinux(LOG):
    # check current state
    (s, out) = commands.getstatusoutput('getenforce')
    current_state = out
    if s != 0:
        LOG.error('getenforce error, please check it')
    else:
        if current_state == correct_state.capitalize():
            LOG.info('SELinux current state is: %s' % current_state)
        else:
            LOG.warn('SELinux current state is: %s' % current_state)
            LOG.error('SELinux state need to be %s ' % correct_state.capitalize())

    # check profile /etc/sysconfig/selinux
    current_conf = commands.getoutput(
        'grep "^SELINUX=" /etc/sysconfig/selinux | cut -d "=" -f 2')
    if current_conf == correct_conf:
        LOG.info('SELinux current conf in profile is: %s' % current_conf)
    else:
        LOG.warn('SELinux current conf in profile is: %s' % current_conf)
        LOG.error('SELinux configuration in profile need to be %s ' % correct_conf)
