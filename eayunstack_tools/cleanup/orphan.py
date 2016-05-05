#!/usr/bin/python

# Cleanup orphan resource

import logging
import threading

from eayunstack_tools.utils import NODE_ROLE, log_disabled
from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.pythonclient import PythonClient
from eayunstack_tools.manage.volume import destroy_volume

from neutronclient.common.exceptions import Conflict
from cinderclient.exceptions import NotFound


pythonclient = PythonClient()
keystoneclient = pythonclient.keystoneclient
novaclient = pythonclient.novaclient
neutronclient = pythonclient.neutronclient
cinderclient = pythonclient.cinderclient
glanceclient = pythonclient.glanceclient

tenants = list()
for tenant in keystoneclient.tenants.list():
    tenants.append(tenant.id)


def make(parser):
    '''Cleanup Resources Who Have No Tenants.'''
    parser.set_defaults(func=orphan)


def orphan(parser):
    logging.disable(logging.INFO)
    if not NODE_ROLE.is_controller():
        LOG.warn('This command can only run on controller node !')
        return

    # run delete orphan
    # run delete servers thread first
    nova_thread = RunNovaThread()
    nova_thread.start()
    nova_thread.join()

    # run other thread parallel
    threads = [RunCinderThread(), RunGlanceThread(),
               RunNetBaseThread(), RunFirewallThread(),
               RunSecgroupThread(), RunVPNThread(),
               RunLBThread(), RunQoSThread()]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    logging.disable(logging.NOTSET)


class BaseCleanupThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        self.orphan()
        self._run()

    def get_tenant(self, resource):
        return resource.tenant_id

    def get_id(self, resource):
        return resource.id

    def orphan_resource(self, resources, tenant_getter=None, id_getter=None):
        if tenant_getter is None:
            tenant_getter = self.get_tenant
        if id_getter is None:
            id_getter = self.get_id

        orphans = list()
        for resource in resources:
            if tenant_getter(resource) not in tenants:
                orphans.append(id_getter(resource))
        return orphans

    def base_delete(self, resource_name, resource_ids, delete_func):
        no_log_resources = []
        while resource_ids:
            for resource_id in resource_ids:
                # avoid LOG delete info many times
                if resource_id not in no_log_resources:
                    with log_disabled():
                        LOG.info('Delete %s [%s]' % (
                            resource_name, resource_id))
                        no_log_resources.append(resource_id)
                try:
                    delete_func(resource_id)
                    # delete successfully, break
                    resource_ids.remove(resource_id)
                    break
                except Conflict:
                    # retry: deal with conflict.
                    continue
                except NotFound:
                    # when call destroy_volume(),
                    # will delete volumes and snapshots,
                    # if snapshots NotFound, do nothing.
                    resource_ids.remove(resource_id)
                    break
                except Exception as e:
                    LOG.warn('Can not delete %s [%s]'
                             % (resource_name, resource_id))
                    LOG.error(e)
                    # something else wrong, break, won't retry
                    resource_ids.remove(resource_id)
                    break


class RunNovaThread(BaseCleanupThread):
    def orphan(self):
        self.servers = self.orphan_resource(
            novaclient.servers.list(search_opts={'all_tenants': 1}))

    def _run(self):
        self.base_delete('instance', self.servers,
                         novaclient.servers.delete)


class RunCinderThread(BaseCleanupThread):
    def orphan(self):
        self.snapshots = self.orphan_resource(
            cinderclient.volume_snapshots.list(search_opts={'all_tenants': 1}),
            tenant_getter=lambda snapshot:
                pythonclient.cinder_get_tenant_id(snapshot.id))

        self.volumes = self.orphan_resource(
            cinderclient.volumes.list(search_opts={'all_tenants': 1}),
            tenant_getter=lambda volume:
                volume.__dict__['os-vol-tenant-attr:tenant_id'])

    def _run(self):
        for volume_id in self.volumes:
            try:
                with log_disabled():
                    LOG.info('Delete volume [%s]' % volume_id)
                cinderclient.volumes.delete(volume_id)
            except Exception:
                with log_disabled():
                    LOG.info('Destroy volume [%s]' % volume_id)
                destroy_volume(volume_id, interactive=False)
        self.base_delete('snapshot', self.snapshots,
                         cinderclient.volume_snapshots.delete)


class RunGlanceThread(BaseCleanupThread):
    def orphan(self):
        self.images = self.orphan_resource(
            glanceclient.images.list(),
            tenant_getter=lambda image: image['owner'],
            id_getter=lambda image: image['id'])

    def _run(self):
        self.base_delete('image', self.images,
                         glanceclient.images.delete)


class RunNetBaseThread(BaseCleanupThread):
    @property
    def orphan_ports(self):
        orphans = list()
        for port in neutronclient.list_ports()['ports']:
            network_id = port['network_id']
            # if network is orphan, port is orphan, too.
            if network_id in self.networks:
                orphans.append(port['id'])
        return orphans

    def orphan(self):
        self.networks = self.orphan_resource(
            neutronclient.list_networks()['networks'],
            tenant_getter=lambda network: network['tenant_id'],
            id_getter=lambda network: network['id'])

        self.subnets = self.orphan_resource(
            neutronclient.list_subnets()['subnets'],
            tenant_getter=lambda subnet: subnet['tenant_id'],
            id_getter=lambda subnet: subnet['id'])

        self.routers = self.orphan_resource(
            neutronclient.list_routers()['routers'],
            tenant_getter=lambda router: router['tenant_id'],
            id_getter=lambda router: router['id'])

        self.floatingips = self.orphan_resource(
            neutronclient.list_floatingips()['floatingips'],
            tenant_getter=lambda floatingip: floatingip['tenant_id'],
            id_getter=lambda floatingip: floatingip['id'])

        self.ports = self.orphan_ports

    def _run(self):
        self.base_delete('floating ip', self.floatingips,
                         neutronclient.delete_floatingip)

        for port_id in self.ports:
            try:
                with log_disabled():
                    LOG.info('Delete port [%s]' % port_id)
                neutronclient.delete_port(port_id)
            except Conflict as e:
                with log_disabled():
                    LOG.info('  Solving conflict: remove interface...')
                router_id = neutronclient.show_port(port_id)['port']['device_id']
                neutronclient.remove_interface_router(
                    router_id,
                    {'port_id': port_id})
            except Exception as e:
                LOG.warn('Can not delete port [%s]' % port_id)
                LOG.error(e)

        # if firewall create with target router,
        # CAN NOT delete router before firewall is deleted.
        # NOTE: already add retry
        self.base_delete('router', self.routers,
                         neutronclient.delete_router)
        self.base_delete('subnet', self.subnets,
                         neutronclient.delete_subnet)
        self.base_delete('network', self.networks,
                         neutronclient.delete_network)


class RunFirewallThread(BaseCleanupThread):
    def orphan(self):
        self.firewalls = self.orphan_resource(
            neutronclient.list_firewalls()['firewalls'],
            tenant_getter=lambda firewall: firewall['tenant_id'],
            id_getter=lambda firewall: firewall['id'])

        self.firewall_policies = self.orphan_resource(
            neutronclient.list_firewall_policies()['firewall_policies'],
            tenant_getter=lambda firewall_policy: firewall_policy['tenant_id'],
            id_getter=lambda firewall_policy: firewall_policy['id'])

        self.firewall_rules = self.orphan_resource(
            neutronclient.list_firewall_rules()['firewall_rules'],
            tenant_getter=lambda firewall_rule: firewall_rule['tenant_id'],
            id_getter=lambda firewall_rule: firewall_rule['id'])

    def _run(self):
        self.base_delete('firewall', self.firewalls,
                         neutronclient.delete_firewall)
        self.base_delete('firewall policy', self.firewall_policies,
                         neutronclient.delete_firewall_policy)
        self.base_delete('firewall rule', self.firewall_rules,
                         neutronclient.delete_firewall_rule)


class RunSecgroupThread(BaseCleanupThread):
    def orphan(self):
        self.secgroups = self.orphan_resource(
            neutronclient.list_security_groups()['security_groups'],
            tenant_getter=lambda secgroup: secgroup['tenant_id'],
            id_getter=lambda secgroup: secgroup['id'])

    def _run(self):
        # delete secgroup, and rules will be deleted, too.
        self.base_delete('security group', self.secgroups,
                         neutronclient.delete_security_group)


class RunVPNThread(BaseCleanupThread):
    def orphan(self):
        self.ikepolicies = self.orphan_resource(
            neutronclient.list_ikepolicies()['ikepolicies'],
            tenant_getter=lambda ikepolicy: ikepolicy['tenant_id'],
            id_getter=lambda ikepolicy: ikepolicy['id'])

        self.ipsecpolicies = self.orphan_resource(
            neutronclient.list_ipsecpolicies()['ipsecpolicies'],
            tenant_getter=lambda ipsecpolicy: ipsecpolicy['tenant_id'],
            id_getter=lambda ipsecpolicy: ipsecpolicy['id'])

        self.vpnservices = self.orphan_resource(
            neutronclient.list_vpnservices()['vpnservices'],
            tenant_getter=lambda vpnservice: vpnservice['tenant_id'],
            id_getter=lambda vpnservice: vpnservice['id'])

        self.ipsec_site_conns = self.orphan_resource(
            neutronclient.list_ipsec_site_connections()['ipsec_site_connections'],
            tenant_getter=lambda ipsec_site_conn: ipsec_site_conn['tenant_id'],
            id_getter=lambda ipsec_site_conn: ipsec_site_conn['id'])

    def _run(self):
        self.base_delete('IPSEC site connection', self.ipsec_site_conns,
                         neutronclient.delete_ipsec_site_connection)
        self.base_delete('VPN service', self.vpnservices,
                         neutronclient.delete_vpnservice)
        self.base_delete('IPSEC policy', self.ipsecpolicies,
                         neutronclient.delete_ipsecpolicy)
        self.base_delete('IKE policy', self.ikepolicies,
                         neutronclient.delete_ikepolicy)


class RunLBThread(BaseCleanupThread):
    def orphan(self):
        self.vips = self.orphan_resource(
            neutronclient.list_vips()['vips'],
            tenant_getter=lambda vip: vip['tenant_id'],
            id_getter=lambda vip: vip['id'])

        self.health_monitors = self.orphan_resource(
            neutronclient.list_health_monitors()['health_monitors'],
            tenant_getter=lambda health_monitor: health_monitor['tenant_id'],
            id_getter=lambda health_monitor: health_monitor['id'])

        self.members = self.orphan_resource(
            neutronclient.list_members()['members'],
            tenant_getter=lambda member: member['tenant_id'],
            id_getter=lambda member: member['id'])

        self.pools = self.orphan_resource(
            neutronclient.list_pools()['pools'],
            tenant_getter=lambda pool: pool['tenant_id'],
            id_getter=lambda pool: pool['id'])

    def _run(self):
        self.base_delete('VIP', self.vips,
                         neutronclient.delete_vip)
        self.base_delete('health monitor', self.health_monitors,
                         neutronclient.delete_health_monitor)
        self.base_delete('member', self.members,
                         neutronclient.delete_member)
        self.base_delete('pool', self.pools,
                         neutronclient.delete_pool)


class RunQoSThread(BaseCleanupThread):
    def orphan(self):
        self.qoss = self.orphan_resource(
            neutronclient.list_eayun_qoss()['qoss'],
            tenant_getter=lambda qos: qos['tenant_id'],
            id_getter=lambda qos: qos['id'])

    def _run(self):
        # delete qos, and queue and filter will be deleted, too.
        self.base_delete('QoS', self.qoss,
                         neutronclient.delete_eayun_qos)
