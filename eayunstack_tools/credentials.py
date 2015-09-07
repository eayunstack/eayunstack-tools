import commands

ENV_VAR_FILE = '/root/openrc'

(s, o) = commands.getstatusoutput('source %s; \
                                echo OS_AUTH_URL=$OS_AUTH_URL; \
                                echo OS_USERNAME=$OS_USERNAME; \
                                echo OS_PASSWORD=$OS_PASSWORD; \
                                echo OS_TENANT_NAME=$OS_TENANT_NAME; \
                                echo OS_REGION_NAME=$OS_REGION_NAME' \
                                % ENV_VAR_FILE)
if s == 0:
    var = {}
    for v in o.split('\n'):
        var[v.split('=')[0]]=v.split('=')[1]

def get_nova_credentials_v2():
    d = {}
    d['version'] = '2'
    d['username'] = var['OS_USERNAME']
    d['api_key'] = var['OS_PASSWORD']
    d['auth_url'] = var['OS_AUTH_URL']
    d['project_id'] = var['OS_TENANT_NAME']
    return d

def get_cinder_credentials():
    d = {}
    d['username'] = var['OS_USERNAME']
    d['api_key'] = var['OS_PASSWORD']
    d['auth_url'] = var['OS_AUTH_URL']
    d['project_id'] = var['OS_TENANT_NAME']
    return d

def get_neutron_credentials():
    d = {}
    d['username'] = var['OS_USERNAME']
    d['password'] = var['OS_PASSWORD']
    d['auth_url'] = var['OS_AUTH_URL']
    d['tenant_name'] = var['OS_TENANT_NAME']
    return d

def get_keystone_credentials():
    d = {}
    d['username'] = var['OS_USERNAME']
    d['password'] = var['OS_PASSWORD']
    d['auth_url'] = var['OS_AUTH_URL']
    d['tenant_name'] = var['OS_TENANT_NAME']
    return d
