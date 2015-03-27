#check network 
import logging
import glob
import commands
from eayunstack_tools.doctor.utils import valid_print, set_logger

def check_network(LOG):
    # 1) find all network and their link status
    tmp = glob.glob('/sys/class/net/*/device')
    nics = dict()
    for i in tmp:
        name = i.split('/')[4]
        (status, out) = commands.getstatusoutput(
            "ethtool %s | \grep 'Link detected:'" % (name))
        if 'yes' in out:
            status = 'yes'
        else:
            status = 'no'
        nics[name] = status

    # TODO: print the function of nics, e.g. for managerment or storage
    LOG.info('Network card information:')
    for i in nics.keys():
        valid_print(i, nics[i])

    # 2) check all NIC network connectivity

        # how to check ???
