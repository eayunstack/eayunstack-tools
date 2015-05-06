import os
import re
import ConfigParser
import logging
import commands
import MySQLdb
import socket
from eayunstack_tools.logger import fmt_print
from eayunstack_tools.doctor.config import get_db_profile, get_component_check_cmd
from eayunstack_tools.doctor.config import *
from eayunstack_tools.doctor.utils import get_node_role, check_service
from eayunstack_tools.utils import NODE_ROLE, ssh_connect

LOG = logging.getLogger(__name__)

node_role = get_node_role()

def check_profile(profile, role):
    # if the profile file is not exists, go back
    if not os.path.exists(profile):
        LOG.error('Can not find this profile. Abort this check!')
        return

    # get template path
    template = get_template_path(profile, role)

    # if the template file is not exists, go back
    if not os.path.exists(template):
        LOG.error('Template file is missing, Please check it by yourself.')
        return

    if role is not 'mongo':
        # check file resolvability, if not resolvability, go back
        for filepath in (profile, template):
            if not check_file_resolvability(filepath):
                return
        
        # Check profile keys
        check_list = get_check_list(profile)
        for section in sorted(check_list.keys()):
            for key in check_list[section]:
               check_key(section, key, profile, template)

        # some keys in template but not in profile(named lost keys)
        t_check_list = get_check_list(template)
        for t_section in sorted(t_check_list.keys()):
            for t_key in t_check_list[t_section]:
                check_lost_key(t_section, t_key, profile)
    else:
        # Check profile keys
        check_list = get_check_list_common(profile)
        for key in check_list:
            check_key_common(key, profile, template)

        # some keys in template but not in profile(named lost keys)
        t_check_list = get_check_list_common(template)
        for t_key in t_check_list:
            check_lost_key_common(t_key, profile)
            
def get_template_path(profile, role):
    (path, profile_name) = os.path.split(profile)
    template_name = profile_name + '.template'
    template_path = '/.eayunstack/template/' + role + '/' + template_name
    return template_path

# return check list like:
# {'DEFAULT': ['admin_token', 'verbose'], 'token': ['driver', 'provider'], 'database': ['connection']}
def get_check_list(filepath):
    '''Get the options list need to check'''
    check_keys = []
    check_list = {}
    p = ConfigParser.ConfigParser()
    p.read(filepath)
    sections = p.sections()
    for section in sections:
        items = dict(p.items(section))
        if sorted(items.keys()) != sorted(p.defaults().keys()):
            for key in items.keys():
                if key not in p.defaults().keys():
                    check_keys.append(key)
            check_list[section]=check_keys
            check_keys = []
    
    # add [DEFAULT] section to check_list
    if len(dict(p.defaults()).keys()) > 0:
        check_list['DEFAULT']=dict(p.defaults()).keys()
    
    return check_list 

def get_check_list_common(filepath):
    (s, o) = commands.getstatusoutput('grep -v "^$" %s | grep -v "^#" | cut -d "=" -f 1' % filepath)
    if s != 0:
        LOG.error('Can not get check options list ! Please check file: %s.' % filepath)
    else:
        check_list_common = []
        for key in o.split('\n'):
            check_list_common.append(key.strip())
        return check_list_common

def check_key(section, key, profile, template):
    pp = ConfigParser.ConfigParser()
    pp.read(profile)
    pt = ConfigParser.ConfigParser()
    pt.read(template)

    current_value = dict(pp.items(section))[key]
    try:
        correct_value = dict(pt.items(section))[key]
    # there is no this section in the template file
    except ConfigParser.NoSectionError:
        LOG.warn('Can not check following option, please check it by yourself. ')
        fmt_print('[%s] ' % section)
        fmt_print('%s=%s' % (key, current_value))
        correct_value = current_value
    # there is no this key in the section
    except KeyError:
        LOG.warn('Can not check following option, please check it by yourself. ')
        fmt_print('[%s] ' % section)
        fmt_print('%s=%s' % (key, current_value))
        correct_value = current_value

    # if the key in profile and template didn't matched, check faild
    if current_value != correct_value:
        LOG.error('[%s] ' % section)
        LOG.error('"%s" option check faild' % key)
        fmt_print('Current is "%s=%s"' % (key, current_value))
        fmt_print('Correct is "%s=%s"' % (key, correct_value))

def check_key_common(key, profile, template):
    current_value = get_value_common(key, profile)
    correct_value = get_value_common(key, template)
    if not correct_value:
        LOG.warn('Can not check following option, please check it by yourself. ')
        fmt_print('%s=%s' % (key, current_value))
    elif current_value != correct_value:
        LOG.error('"%s" option check faild' % key)
        fmt_print('Current is "%s=%s"' % (key, current_value))
        fmt_print('Correct is "%s=%s"' % (key, correct_value))
    

def get_value_common(key, filepath):
    (s, o) = commands.getstatusoutput('grep "^%s" %s | cut -d "=" -f 2' % (key, filepath))
    if s != 0 or o is None:
        LOG.error('Can not get %s\'s value ! Please check file: %s.' % (key, filepath))
    return o.strip()

# if the section or key not in the profile, warnning
def check_lost_key(section, key, profile):
    p = ConfigParser.ConfigParser()
    p.read(profile)
    try:
        dict(p.items(section))[key]
    except ConfigParser.NoSectionError:
        LOG.warn('Lost section [%s] in this profile.' % section)
    except KeyError:
        LOG.warn('Lost [%s] ==> %s option in this profile. Please check it.' % (section, key))

# if the section or key not in the profile, warnning
def check_lost_key_common(key, profile):
    profile_keys = get_check_list_common(profile)
    if key not in profile_keys:
        LOG.warn('Lost "%s" option in this profile. Please check it.' % key)

def check_file_resolvability(filepath):
    tp = ConfigParser.ConfigParser()
    try:
        tp.read(filepath)
    except ConfigParser.ParsingError, msg:
        LOG.error(msg)
        LOG.error('Abort this check!')
        return False
    return True

def check_db_connect(component):
    try:
        cp = ConfigParser.ConfigParser()
        cp.read(get_db_profile()[component])
        # glance's db connection configuration in the profile is
        # 'sql_connection' in eayunstack environment
        if component == 'glance':
            value = cp.get('database', 'sql_connection')
        else:
            value = cp.get('database', 'connection')
        p = re.compile(r'mysql://(.+):(.+)@(.+)/(.+)\?(.+)')
        m = p.match(value).groups()
        check_mysql_connect(m[2], m[0], m[1], m[3])
    except:
        LOG.error('Load DB Configuration Faild.')
    
def check_mysql_connect(server, user, pwd, dbname):
    try:
        db = MySQLdb.connect(server, user, pwd, dbname)
        cursor = db.cursor()
        cursor.execute('SELECT VERSION()')
        cursor.fetchone()
        db.close()
        fmt_print('Check Sucessfully.')
    except:
        LOG.error('Check Faild.')

def check_component_availability(component, check_cmd):
    ENV_FILE_PATH = '/root/openrc'
    if os.path.exists(ENV_FILE_PATH):
        (s, o) = commands.getstatusoutput('source %s;' % ENV_FILE_PATH + check_cmd)
        if s == 0:
            fmt_print('Check Successfully.')
        else:
            LOG.error('Check Faild.')
            LOG.error(o)
    else:
        LOG.error('Can not load environment variables from "%s".' % ENV_FILE_PATH)

def check_node_profiles(role):
    component_list = eval('get_%s_component' % role)()
    for c in component_list:
        LOG.info('Checking "%s" Component' % c.capitalize())
        profile_list = eval('get_%s_profiles' % c)()
        for p in profile_list:
            fmt_print('Profile: ' + p)
            check_profile(p, role)

def check_node_services(node):
    component_list = eval('get_%s_component' % node)()
    check_cmd = get_component_check_cmd()
    for c in component_list:
        LOG.info('Checking "%s" Component' % c.capitalize())
        LOG.info('-Service Status')
        if c == 'nova':
            service_list = eval('get_%s_%s_services' % (node, c))()
        else:
            service_list = eval('get_%s_services' % c)()
        for s in service_list:
           # utils.check_service(s)
            check_service(s)
        if node != 'controller':
            continue
        LOG.info('-DB Connectivity')
        check_db_connect(c)
        LOG.info('-Service Availability')
        check_component_availability(c, check_cmd[c])

# get all nodes list
# return like following list
# ['192.168.2.32','192.168.2.33','192.168.3.251']
def get_node_list(role):
    node_list = []
    try:
        for node in NODE_ROLE.nodes:
            if node['roles'] == role:
                node_list.append(node['ip'])
    except:
        LOG.error('Can not get the node list !')
        node_list = []
    return node_list

def check_nodes(node_role, check_obj, multi_role=False):
    if multi_role:
        check_cmd = 'eayunstack doctor stack --' + check_obj
    else:
        check_cmd = 'eayunstack doctor stack --' + check_obj + ' --%s' % node_role
    node_list = get_node_list(node_role)
    if len(node_list) == 0:
        LOG.warn('Node list is null !')
        return
    for node in node_list:
        LOG.info('%s Role: %-10s Node: %-13s %s' % ('*'*15, node_role, node, '*'*15))
        # ssh to node and run command
        result_out,result_err = ssh_connect(node, check_cmd)
        print result_out
