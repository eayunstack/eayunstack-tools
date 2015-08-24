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
