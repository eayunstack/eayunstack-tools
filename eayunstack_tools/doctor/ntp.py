#check ntp
import commands
from utils import check_service, set_logger
import re

def check_ntp(LOG):
    check_service('ntpd')
    (s, out) = commands.getstatusoutput(
        'ntpstat | grep "synchronised to NTP server"')
    if s != 0:
        LOG.error('ntpstat error, please check it')
        return
    else:
        p = re.compile(r'.+\((.+)\).+')
        try:
            server = p.match(out).groups()[0]
            LOG.info('ntpserver is %s', server)
        except:
            LOG.error('except ntpstate error, please check it')
            return
