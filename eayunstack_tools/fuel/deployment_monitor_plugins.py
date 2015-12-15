import logging
import yaml
import os
import commands
import getpass
from multiprocessing import Process
from eayunstack_tools.utils import NODE_ROLE, get_fuel_node_ip, logging_disable
from eayunstack_tools.sys_utils import ssh_connect, ssh_connect2
from eayunstack_tools.sys_utils import scp_connect, scp_connect2
from eayunstack_tools.sys_utils import run_command_on_node

from eayunstack_tools.logger import StackLOG as LOG

INFLUXDB_HOST = ''
CONF_TMP_DIR = '/root/.plugin_conf/'
ASTUTE_CONF_FILEPATH = CONF_TMP_DIR + 'astute.yaml'
GLOBALS_CONF_FILEPATH = CONF_TMP_DIR + 'globals.yaml'
COMMON_CONF_FILEPATH = CONF_TMP_DIR + 'common.yaml'
HIERA_CONF_FILEPATH = CONF_TMP_DIR + 'hiera.yaml'
INFLUXDB_REPO_CONF_FILEPATH = CONF_TMP_DIR + 'influxdb-grafana.repo'
NAILGUN_REPO_CONF_FILEPATH = CONF_TMP_DIR + 'nailgun.repo'
LMA_REPO_CONF_FILEPATH = CONF_TMP_DIR + 'lma_collector.repo'
INSTALL_PACKAGES = 'puppet rsync iptables-services'

def deployment_monitor_plugins(parser):
    if not NODE_ROLE.is_fuel():
        LOG.warn('This command can only run on fuel node !')
        return
    if parser.INFLUXDB:
        deployment_influxdb_grafana(parser.ENV)
    if parser.LMA_COLLECTOR:
        deployment_lma_collector(parser.ENV)

def make(parser):
    """
    Deploy fuel monitor plugins.
    """
    parser.add_argument(
        '--env',
        required=True,
        dest='ENV',
        help='The fuel environment to be deployment.'
    )
    parser.add_argument(
        '--influxdb',
        dest='INFLUXDB',
        action='store_true',
        default=False,
        help='Deployment influxdb node.',
    )
    parser.add_argument(
        '--lma_collector',
        dest='LMA_COLLECTOR',
        action='store_true',
        default=False,
        help='Deployment lma_collector on openstack node.',
    )
    parser.set_defaults(func=deployment_monitor_plugins)

def deployment_influxdb_grafana(env):
    fuel_node_ip = get_fuel_node_ip(env)
    # 0) get influxdb node IP address, and push ssh pub key to this node.
    if not push_sshpubkey_to_influxdbnode():
        return
    # 1) get influxdb params, and generate influxdb node conf file.
    generate_conf_file(CONF_TMP_DIR, fuel_node_ip)
    # 2) push conf file to influxdb node
    push_conf_file_to_influxdbnode()
    push_hiera_yaml_to_node(INFLUXDB_HOST, HIERA_CONF_FILEPATH)
    # 3) install rpm packages on influxdb node
    install_packages_on_influxdbnode()
    # 4) rsync plugin modules on influxdb node
    rsync_plugin_modules_on_node(INFLUXDB_HOST, 'influxdb_grafana', fuel_node_ip)
    # 5) deployment influxdb/grafana on influxdb node
    deployment_influxdbnode()

def push_sshpubkey_to_influxdbnode():
    INFLUXDB_HOST = raw_input('Please entry the ip address of influxdb node: ')
    global INFLUXDB_HOST
    root_pw = getpass.getpass(prompt='Please entry the root\'s password of influxdb node: ')
    local_ssh_pubkey_file = os.environ['HOME'] + '/.ssh/id_rsa.pub'
    remote_authorized_keys_file = '/root/.ssh/authorized_keys'
    if scp_connect2(INFLUXDB_HOST, local_ssh_pubkey_file, remote_authorized_keys_file,
                'root', root_pw):
        return True
    else:
        return False

def generate_conf_file(conf_dir, fuel_node_ip):
    LOG.info('Generate conf file .')
    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)
    _generate_astute_conf_file(ASTUTE_CONF_FILEPATH)
    _generate_plugin_repo_conf('influxdb_grafana', INFLUXDB_REPO_CONF_FILEPATH, fuel_node_ip)
    _generate_nailgun_repo_conf_file(NAILGUN_REPO_CONF_FILEPATH, fuel_node_ip)
    _generate_common_conf_file(COMMON_CONF_FILEPATH)
    _generate_hiera_conf_file(HIERA_CONF_FILEPATH)

def _generate_astute_conf_file(file_path):
    influxdb_conf_def = {
        'influxdb_dbname': 'lma',
        'influxdb_username': 'lma',
        'influxdb_userpass': 'lmapass',
        'influxdb_rootpass': 'admin'
    }
    influxdb_conf = {}
    for key in influxdb_conf_def:
        influxdb_conf[key] = _get_param(key, influxdb_conf_def[key])
    influxdb_conf['data_dir'] = '/opt/influxdb'
    influxdb_conf['node_name'] = 'influxdb'
    astute_conf = {'influxdb_grafana': influxdb_conf,
                    'user_node_name': 'influxdb',
                    'roles': ['base-os'],
                    'use_neutron': True}
    LOG.debug('Generate %s' % file_path)
    with open(file_path, 'w') as astute_yaml:
        astute_yaml.write(yaml.dump(astute_conf, default_flow_style=False))

def _get_param(key, def_value=None):
    value = raw_input('Please entry %s [%s]: ' % (key, def_value))
    return value if value else def_value

def _generate_nailgun_repo_conf_file(file_path, fuel_node_ip):
    repo_name = 'nailgun'
    baseurl = 'http://' \
            + fuel_node_ip \
            + ':8080/2014.2.2-6.0.1/centos/x86_64'
    gpgcheck = 0
    repo_conf = '[' + repo_name + ']' + '\n' \
                + 'name=' + repo_name + '\n' \
                + 'baseurl=' + baseurl + '\n' \
                + 'gpgcheck=' + str(gpgcheck)
    LOG.debug('Generate %s' % file_path)
    with open(file_path, 'w') as repo_conf_file:
        repo_conf_file.write(repo_conf)

def _generate_common_conf_file(file_path):
    common_conf = {'influxdb_address': INFLUXDB_HOST}
    LOG.debug('Generate %s' % file_path)
    with open(file_path, 'w') as common_yaml:
        common_yaml.write(yaml.dump(common_conf, default_flow_style=False))

def _generate_hiera_conf_file(file_path):
    hiera_conf = {':backends': ['yaml'],
                ':hierarchy': ['globals', 'astute'],
                ':yaml': {':datadir': '/etc/hiera'},
                ':logger': ['noop']}
   # hiera_conf[':backends'] = ['yaml']
   # hiera_conf[':hierarchy'] = ['globals', 'astute']
   # hiera_conf[':yaml'] = {':datadir': '/etc/hiera'}
   # hiera_conf[':logger'] = ['noop']
    LOG.debug('Generate %s' % file_path)
    with open(file_path, 'w') as hiera_yaml:
        hiera_yaml.write(yaml.dump(hiera_conf, default_flow_style=False))

@logging_disable
def get_plugin_version(plugin_name):
    plugin_version = None
    from fuelclient.client import APIClient
    plugins = APIClient.get_request("plugins")
    for plugin in plugins:
        if plugin['name'] == plugin_name:
            plugin_version = plugin['version']
    return plugin_version

def push_conf_file_to_influxdbnode():
    LOG.info('Push conf file to influxdb node.')
    push_repo_file_to_node(INFLUXDB_HOST, 'influxdb_grafana',
                    INFLUXDB_REPO_CONF_FILEPATH, backup=True)
    push_repo_file_to_node(INFLUXDB_HOST, 'nailgun',
                    NAILGUN_REPO_CONF_FILEPATH)
    push_yaml_to_node(INFLUXDB_HOST, ASTUTE_CONF_FILEPATH, 'astute.yaml')

def install_packages_on_influxdbnode():
    LOG.info('Install rpm packages "%s" on node %s .'
                % (INSTALL_PACKAGES, INFLUXDB_HOST))
    (out, err) = ssh_connect(INFLUXDB_HOST, 'yum -d 0 -e 0 -y install %s'
                                % INSTALL_PACKAGES)
    if out != '':
        log_split_output(out, 'warn')

def rsync_plugin_modules_on_node(host, plugin_name, fuel_node_ip):
    LOG.debug('Sync plugin modules on node %s .' % host)
    plugin_version = get_plugin_version(plugin_name)
    modules_path = 'rsync://' \
                   + fuel_node_ip \
                   + ':/plugins/' \
                   + plugin_name \
                   + '-' \
                   + plugin_version \
                   + '/deployment_scripts/puppet/'
    plugin_dir = '/etc/fuel/plugins/' \
                + plugin_name \
                + '-' \
                + plugin_version \
                + '/puppet'
    (out, err) = ssh_connect(host,
                    'test -d %s || mkdir -p %s' % (plugin_dir, plugin_dir))
    if err != '':
        log_split_output(err, 'error')
    (out, err) = ssh_connect(host,
                'rsync -vzrtopg %s %s' % (modules_path, plugin_dir))
    if err != '':
        log_split_output(err, 'error')

def deployment_influxdbnode():
    LOG.info('Deploy influxdb/grafana on node %s .' % INFLUXDB_HOST)
    plugin_version = get_plugin_version('influxdb_grafana')
    manifest_path = '/etc/fuel/plugins/influxdb_grafana' \
                    + '-' \
                    + plugin_version \
                    + '/puppet/manifests/'
    module_path = '/etc/fuel/plugins/influxdb_grafana' \
                    + '-' \
                    + plugin_version \
                    + '/puppet/modules/'
    manifest_list = ['check_environment_configuration.pp',
                     'eayunstack_netconfig.pp',
                     'firewall.pp',
                     'setup_influxdir.pp',
                     'influxdb.pp',
                     'grafana.pp']
    for manifest in manifest_list:
        if not _puppet_apply(INFLUXDB_HOST, module_path,
                        manifest_path + manifest):
            break

def _puppet_apply(host, module_path, manifest):
    success = False
    log_file = '/var/log/deployment_influxdb.log'
    cmd =  ('puppet apply --modulepath=%s -l %s --debug %s || echo $?'
            % (module_path, log_file, manifest))
    LOG.info('Apply manifest %s on node %s .' 
                % (os.path.basename(manifest), host))
    (out, err) = ssh_connect(host, cmd)
    if out != '':
        LOG.error('Apply manifest %s on node %s failed .' 
                    'Please check %s on node %s .'
                    % (os.path.basename(manifest), host, log_file, host))
    else:
        success = True
        LOG.debug('Apply manifest %s on node-%s successfully .' 
                    % (os.path.basename(manifest), host))
    return success

def puppet_apply2(host_id, module_path, manifest):
    log_file = '/var/log/lma_collector_deployment.log'
    cmd =  ('puppet apply --modulepath=%s -l %s  --debug %s'
            % (module_path, log_file, manifest))
    LOG.debug('Apply manifest %s on node-%s .' 
                % (os.path.basename(manifest), host_id))
    (_, _, exitcode) = run_command_on_node(host_id, cmd)
    if exitcode == 0:
        LOG.debug('Apply manifest %s on node-%s successfully .' 
                    % (os.path.basename(manifest), host_id))
    else:
        LOG.error('Apply manifest %s on node-%s failed .' 
                    'Please check %s on node-%s .'
                    % (os.path.basename(manifest), host_id, log_file, host_id))

def deployment_lma_collector(env):
    fuel_node_ip = get_fuel_node_ip(env)
    # 0) get nodes_info & check all openstack node is online
    nodes_info = get_nodes_info(env)
    if not check_all_openstack_node_online(nodes_info):
        return
    # 1) get lma_collector params, and generate conf file.
    generate_lma_conf_file(CONF_TMP_DIR, nodes_info, fuel_node_ip)
    # 2) push conf file to openstack node
    push_conf_file_to_openstack_node(nodes_info)
    push_hiera_to_openstack_nodes(nodes_info)
    # 3) create symbolic links for astute.yaml on openstack node
    create_symbolic_links_on_openstack_node(nodes_info)
    # 4) rsync plugin modules on openstack node
    rsync_plugin_modules_on_openstack_node(nodes_info, fuel_node_ip)
    # 5) deployment influxdb/grafana on influxdb node
    deployment_openstack_nodes(nodes_info)

def generate_lma_conf_file(conf_dir, nodes_info, fuel_node_ip):
    LOG.info('Generate openstack node conf file.')
    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)
    for node in nodes_info:
        br_fw_mgmt = node['fuelweb_admin'].split('/')[0]
        br_mgmt = str(node['management'].split('/')[0])
        file_path = GLOBALS_CONF_FILEPATH + '-' + br_fw_mgmt
        _generate_globals_conf_file(file_path, br_mgmt)
    _generate_plugin_repo_conf('lma_collector', LMA_REPO_CONF_FILEPATH, fuel_node_ip)

def _generate_globals_conf_file(file_path, internal_address):
    f = open(ASTUTE_CONF_FILEPATH)
    astute = yaml.load(f)
    ff = open(COMMON_CONF_FILEPATH)
    common = yaml.load(ff)
    lma_conf = {
        'environment_label': 'EayunStack',
        'influxdb_mode': 'remote',
        'influxdb_database': astute['influxdb_grafana']['influxdb_dbname'],
        'influxdb_address': common['influxdb_address'],
        'influxdb_user': astute['influxdb_grafana']['influxdb_username'],
        'influxdb_password': astute['influxdb_grafana']['influxdb_userpass'],
        'elasticsearch_mode': 'disabled',
    }
    globals_conf = {}
    globals_conf['lma_collector'] = lma_conf
    globals_conf['internal_address'] = internal_address
    LOG.debug('Generate %s' % file_path)
    with open(file_path, 'w') as globals_yaml:
        globals_yaml.write(yaml.dump(globals_conf, default_flow_style=False))

def push_conf_file_to_openstack_node(nodes_info):
    LOG.info('Push conf file to openstack node.')
    for node in nodes_info:
        host = str(node['fuelweb_admin'].split('/')[0])
        push_repo_file_to_node(host, 'lma_collector',
                                LMA_REPO_CONF_FILEPATH)
        src_path = CONF_TMP_DIR + 'globals.yaml' + '-' + host
        dst_file_name = 'globals.yaml'
        push_yaml_to_node(host, src_path, dst_file_name)

def create_symbolic_links_on_openstack_node(nodes_info):
    LOG.info('Create symbolic links on openstack node.')
    for node in nodes_info:
        host = str(node['fuelweb_admin'].split('/')[0])
        src_file = '/etc/astute.yaml'
        dst_file = '/etc/hiera/astute.yaml'
        cmd = 'test -h ' + dst_file + ' || ln -s ' + src_file + ' ' + dst_file
        (out, err) = ssh_connect(host, cmd)
        if err != '':
            LOG.error('Can not run command: %s on node %s .' % (cmd, host))
        else:
            LOG.debug('Create symbolic links on node %s .' % host)

def rsync_plugin_modules_on_openstack_node(nodes_info, fuel_node_ip):
    LOG.info('Rsync plugin modules on openstack node.')
    for node in nodes_info:
        host = str(node['fuelweb_admin'].split('/')[0])
        rsync_plugin_modules_on_node(host, 'lma_collector', fuel_node_ip)

def deployment_openstack_nodes(nodes_info):
    LOG.info('Deployment lma_collector on openstack nodes.')
    plugin_version = get_plugin_version('lma_collector')
    proc_list = []
    for node in nodes_info:
        proc=Process(target=deployment_openstack_node, args=(node, plugin_version,))
        proc.start()
        proc_list.append(proc)
    for proc in proc_list:
        proc.join()

def deployment_openstack_node(node, plugin_version):
    host_id = str(node['id'])
    host_roles = node['roles']
    LOG.debug('Deploy lma_collector on node-%s .' % host_id)
    plugin_dir = '/etc/fuel/plugins/lma_collector-' \
                + plugin_version \
                + '/puppet/'
    manifest_path = plugin_dir + 'manifests/'
    module_path = plugin_dir + 'modules/'
    manifest_base = ['check_environment_configuration.pp',
                    'base.pp']
    manifest_controller = ['controller.pp']
    manifest_compute = ['compute.pp']
    manifest_ceph_osd = ['ceph_osd.pp']
    manifest_mongo = []
    manifest_list = manifest_base
    for role in host_roles:
        if role == 'controller':
            manifest_list = manifest_list + manifest_controller
        if role == 'compute':
            manifest_list = manifest_list + manifest_compute
        if role == 'ceph-osd':
            manifest_list = manifest_list + manifest_ceph_osd
        if role == 'mongo':
            manifest_list = manifest_list + manifest_mongo
    for manifest in manifest_list:
        puppet_apply2(host_id, module_path, manifest_path + manifest)
    
def _generate_plugin_repo_conf(plugin_name, file_path, fuel_node_ip):
    repo_name = plugin_name
    plugin_version = get_plugin_version(plugin_name)
    if not plugin_version:
        LOG.warn('Can not get the version of plugin '
                 '"%s", skip to generate "repo_name.repo"'
                 % (plugin_name, repo_name))
        return
    baseurl = 'http://' \
            + fuel_node_ip \
            + ':8080/plugins/' \
            + plugin_name \
            + '-' \
            + plugin_version \
            + '/repositories/centos'
    gpgcheck = 0
    repo_conf = '[' + repo_name + ']' + '\n' \
                + 'name=' + repo_name + '\n' \
                + 'baseurl=' + baseurl + '\n' \
                + 'gpgcheck=' + str(gpgcheck)
    LOG.debug('Generate %s' % file_path)
    with open(file_path, 'w') as repo_conf_file:
        repo_conf_file.write(repo_conf)

def push_repo_file_to_node(host, plugin_name, src_path, backup=False):
    LOG.debug('Push %s to node %s .' % (src_path, host))
    if backup:
        ssh_connect2(host, 
                    'test -e /etc/yum.repos.d/bak || mkdir /etc/yum.repos.d/bak/')
        (out, err) = ssh_connect2(host,
                    'mv /etc/yum.repos.d/*.repo /etc/yum.repos.d/bak/')
        if err == '':
            scp_connect(host, src_path,
                        '/etc/yum.repos.d/%s.repo' % plugin_name) 
        else:
            LOG.error('Can not backup "/etc/yum.repos.d/*.repo" on node %s .')
    else:
        scp_connect(host, src_path,
                    '/etc/yum.repos.d/%s.repo' % plugin_name) 

def push_yaml_to_node(host, src_path, dst_file_name):
    (out, err) = ssh_connect2(host,
                    'test -d /etc/hiera || mkdir /etc/hiera')
    if err == '':
        LOG.debug('Push %s to node %s .' 
                    % (src_path, host))
        scp_connect(host, src_path,
                    '/etc/hiera/%s' % dst_file_name)
    else:
        LOG.error('Can not create "/etc/hiera/" on node %s .'
                    % host)

def push_hiera_yaml_to_node(host, src_path):
    LOG.debug('Push %s to node %s .' % (src_path, host))
    scp_connect(host, src_path,
                    '/etc/puppet/hiera.yaml')

@logging_disable
def get_nodes_info(env):
    from fuelclient.objects.environment import Environment
    e = Environment(env)
    nodes_info = []
    for node in e.get_all_nodes():
        node_info = {}
        node_info['id'] = node.data['id']
        node_info['fqdn'] = node.data['fqdn']
        node_info['roles'] = node.data['roles']
        for nic in node.data['network_data']:
            if nic['name'] == 'fuelweb_admin':
                node_info['fuelweb_admin'] = nic['ip']
            if nic['name'] == 'management':
                node_info['management'] = nic['ip']
        nodes_info.append(node_info)
    return nodes_info

def push_hiera_to_openstack_nodes(nodes_info):
    for node in nodes_info:
        host = str(node['fuelweb_admin'].split('/')[0])
        push_hiera_yaml_to_node(host, HIERA_CONF_FILEPATH)

def check_all_openstack_node_online(nodes_info):
    LOG.info('Checking all openstack node is online ...')
    for node in nodes_info:
        host = str(node['fuelweb_admin'].split('/')[0])
        if not check_node_online(host):
            return False
    return True

def check_node_online(host):
    online = False
    (out, err) = ssh_connect(host, 'echo "online test"')
    if out.split('\n')[0] == 'online test':
        LOG.debug('Node %s is online .' % host)
        online = True
    return online

def log_split_output(msg, level):
    for m in msg.split('\n'):
        eval('LOG.%s' % level)(m)

