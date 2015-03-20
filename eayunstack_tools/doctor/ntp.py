#check ntp
import commands
from utils import check_service
from utils import set_logger, userful_msg
import re

def check_ntp(logger):
    userful_msg(logger, 'check_ntp')
    check_service('ntpd')
    (s, out) = commands.getstatusoutput(
        'ntpstat | grep "synchronised to NTP server"')
    if s != 0:
        logger.error('ntpstat error, please check it')
        return
    else:
        p = re.compile(r'.+\((.+)\).+')
        try:
            server = p.match(out).groups()[0]
            logger.info('ntpserver is %s', server)
        except:
            logger.error('except ntpstate error, please check it')
            return
