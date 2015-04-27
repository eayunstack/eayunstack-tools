import paramiko
import socket
import logging
import ConfigParser
from cinder.openstack.common import processutils

LOG = logging.getLogger(__name__)

def ssh_execute(command, timeout=2):
    (hostname, username, password, eqlx_group_name) = get_eqlx_host_info()
    logging.disable(logging.INFO)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname, 22, username=username, password=password, timeout=timeout)
        transport = ssh.get_transport()
        chan = transport.open_session()
        try: 
            chan.invoke_shell()
            get_output(chan, eqlx_group_name)
            chan.send(command + '\r')
            out = get_output(chan, eqlx_group_name)
            return out
        finally:
            chan.close()
    except socket.timeout:
        LOG.error('   SSH connect timeout !')
    except paramiko.ssh_exception.AuthenticationException:
        LOG.error('   SSH connect authentication faild !')
    finally:
        ssh.close()
        logging.disable(logging.NOTSET)

def get_output(chan, eqlx_group_name):
    out = ''
    ending = '%s> ' % eqlx_group_name
    while not out.endswith(ending):
        out += chan.recv(102400)

    return out.splitlines()

def get_eqlx_host_info():
    profile_path = '/etc/cinder/cinder.conf'
    try:
        cp = ConfigParser.ConfigParser()
        cp.read(profile_path)
        host = cp.get('cinder_eqlx', 'san_ip')
        user = cp.get('cinder_eqlx', 'san_login')
        pwd = cp.get('cinder_eqlx', 'san_password')
        group_name = cp.get('cinder_eqlx','eqlx_group_name')
        return host,user,pwd,group_name
    except:
        LOG.error('   Can not get eqlx host infomation !')
    
