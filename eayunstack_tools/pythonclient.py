from eayunstack_tools.credentials import get_nova_credentials_v2, get_cinder_credentials
from novaclient.client import Client as nova_Client
from cinderclient.v2.client import Client as cinder_Client


class PythonClient():
    def __init__(self):
        self.nova_credentials = get_nova_credentials_v2()
        self.cinder_credentials = get_cinder_credentials()
        self.novaclient = nova_Client(**self.nova_credentials)
        self.cinderclient = cinder_Client(**self.cinder_credentials)

    def nova_services_list(self):
        services_list = self.novaclient.services.list()
        return self.obj2dict(services_list)

    def cinder_services_list(self):
        services_list = self.cinderclient.services.list()
        return self.obj2dict(services_list)

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
