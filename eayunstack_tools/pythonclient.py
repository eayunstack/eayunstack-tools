from eayunstack_tools.credentials import get_nova_credentials_v2, get_cinder_credentials, get_neutron_credentials, get_keystone_credentials
from novaclient.client import Client as nova_Client
from cinderclient.v2.client import Client as cinder_Client
from neutronclient.v2_0.client import Client as neutron_Client
from novaclient.exceptions import NotFound
from glanceclient.v2.client import Client as glance_Client
from keystoneclient.v2_0.client import Client as keystone_Client


class PythonClient():
    def __init__(self):
        self.nova_credentials = get_nova_credentials_v2()
        self.cinder_credentials = get_cinder_credentials()
        self.neutron_credentials = get_neutron_credentials()
        self.keystone_credentials = get_keystone_credentials()
        self.novaclient = nova_Client(**self.nova_credentials)
        self.cinderclient = cinder_Client(**self.cinder_credentials)
        self.neutronclient = neutron_Client(**self.neutron_credentials)
        self.keystoneclient = keystone_Client(**self.keystone_credentials)
        glance_endpoint = self.keystone_get_endpoint('image')
        self.glanceclient = glance_Client(glance_endpoint, token=self.keystoneclient.auth_token)

    def nova_services_list(self):
        services_list = self.novaclient.services.list()
        return self.obj2dict(services_list)

    def cinder_services_list(self):
        services_list = self.cinderclient.services.list()
        return self.obj2dict(services_list)

    def neutron_agents_list(self):
        agents_list = self.neutronclient.list_agents()['agents']
        return agents_list

    def obj2dict(self, services_list):
        sl = []
        for service in services_list:
            s = {}
            s['binary'] = service.binary
            s['host'] = service.host
            s['zone'] = service.zone
            s['status'] = service.status
            s['state'] = service.state
            sl.append(s)
        return sl

    def cinder_get_volume(self, volume_id):
        volume = self.cinderclient.volumes.get(volume_id)
        return volume

    def cinder_get_snapshots(self, volume_id):
        snapshots = self.cinderclient.volume_snapshots.list(search_opts={'volume_id': volume_id,'all_tenants': 1})
        return snapshots

    def nova_delete_server_volume(self, server_id, volume_id):
        self.novaclient.volumes.delete_server_volume(server_id, volume_id)

    def nova_server(self, server_id):
        server = self.novaclient.servers.get(server_id)
        return server

    def nova_volume(self, server_id, volume_id):
        volume = self.novaclient.volumes.get_server_volume(server_id, volume_id)
        return volume

    def neutron_delete_port(self, port_id):
        self.neutronclient.delete_port(port_id)

    def nova_flavor(self, flavor_id):
        flavor = self.novaclient.flavors.get(flavor_id)
        return flavor

    def nova_server_exist(self, server_id):
        try:
            self.novaclient.servers.get(server_id)
            return True
        except NotFound:
            return False

    def cinder_get_tenant_id(self, snapshot_id):
        tenant_id = self.cinderclient.volume_snapshots.get(snapshot_id)._info['os-extended-snapshot-attributes:project_id']
        return tenant_id

    def glance_get_images(self, tenant_id):
        images = self.glanceclient.images.list(filters={'owner': tenant_id})
        return images

    def glance_delete_image(self, image_id):
        self.glanceclient.images.delete(image_id)

    def keystone_get_endpoint(self, service_type):
        endpoint = self.keystoneclient.service_catalog.url_for(service_type=service_type)
        return endpoint
