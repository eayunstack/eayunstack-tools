from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.logger import fmt_excep_msg
from eayunstack_tools.utils import NODE_ROLE
from eayunstack_tools.sys_utils import ssh_connect, ssh_connect2
import commands
import json
import re
import sys


# TODO: move to utils.py?
def run_command(cmd):
    reval = None
    run_cmd = 'source /root/openrc;' + cmd
    (status, out) = commands.getstatusoutput(run_cmd)
    if status != 0:
        LOG.error("run %s error: %s" % (run_cmd, out))
    else:
        reval = out
    return reval


# FIXME: some neutronclient does not support json output, hack it
def csv2dict(csv):
    """Convert result format from csv to dict:
csv format:
"id","name","mac_address"
"596afd3e-b60a-41f5-97c3-39495979e6d8","","fa:16:3e:3a:ee:97"
"70cb55cd-d5cb-4c12-8ad2-8edf18c2fa94","","fa:16:3e:f7:e9:8c"

dict format:
[{"id": "596afd3e", "name": "", "mac_address": "fa:16:3e:3a:ee:97"},
{"id": "70cb55cd", "name": "", "mac_address": "fa:16:3e:f7:e9:8c"}]
    """
    field = csv.split('\n')[0]
    p = re.compile(r'"(.*)"')
    column = []
    for i in field.split(','):
        column.append(p.match(i).groups()[0])
    routers = []
    out = csv.split('\n')[1:]
    for r in out:
        router = {}
        r = r.split(',')
        index = 0
        for index in range(len(column)):
            try:
                router[column[index]] = p.match(r[index]).groups()[0]
            except AttributeError:
                router[column[index]] = r[index]
        routers.append(router)
    return routers


def vrouter_get_gw_remote(l3_host, rid):
    cmd = "ip netns exec qrouter-%s ip route show | "\
          "grep 'default' | awk '{print $3}'" % (rid)
    out, err = ssh_connect(l3_host, cmd)
    if not err:
        return out.strip('\n')
    else:
        return None

def vrouter_get_gw_interface(l3_host, rid):
    cmd = "ip netns exec qrouter-%s ip route show | "\
          "grep 'default' | awk '{print $5}'" % (rid)
    out, err = ssh_connect(l3_host, cmd)
    if not err:
        return out.strip('\n')
    else:
        return None

# Some fuck juno deploy doest not support json format of port-show message
def port_result_to_json(out, fmt='json'):
    detail = dict()
    if fmt == 'json':
        _out = json.loads(out)
        detail = dict(map(lambda d: (d['Field'], d['Value']), _out))
        return detail
    elif fmt == 'shell':
        """
admin_state_up="True"
allowed_address_pairs=""
binding:host_id="node-5.eayun.com"
        """
        for l in out.split('\n'):
            p = re.compile(r'(.*)="(.*)"')
            try:
                ret = p.match(l).groups()
                detail[ret[0]] = ret[1]
            except Exception as e:
                LOG.error('failed to get port message: %s' % fmt_excep_msg(e))
        return detail


def port_check_one(pid, l3_host=None):
    def port_log(device_owner, s):
        if device_owner == 'network:router_gateway':
            LOG.warn(s)
        else:
            LOG.error(s)

    fmt = 'json'
    cmd = 'neutron port-show %s -f %s -F status -F admin_state_up '\
          '-F device_owner -F device_id' % (pid, fmt)
    out = run_command(cmd)
    if out:
        detail = port_result_to_json(out, fmt)        
        device_owner = detail['device_owner']
        rid = detail['device_id']
        if l3_host is None:
            # if l3_host is None, it is certain that the function is called
            # via command line, rather than vrouter_check_one, so it's ok
            # to call vrouter_get_l3_host here.
            l3_host = vrouter_get_l3_host(rid)

        # 1) check status of gateway port and interface port
        if detail['status'] != 'ACTIVE':
            port_log(device_owner, "status of port %s[%s] on %s is down"
                     % (device_owner, pid, l3_host))
        if not detail['admin_state_up']:
            port_log(device_owner, "admin_status of port %s[%s] on %s is down"
                     % (device_owner, pid, l3_host))

        # 2) ping external gateway to check network status
        #    and check external interface qos
        LOG.debug('check gateway for port on %s' % (l3_host))
        if device_owner == 'network:router_gateway':
            LOG.debug('this port is external port, check external gateway')
            gw = vrouter_get_gw_remote(l3_host, rid)
            interface = vrouter_get_gw_interface(l3_host, rid)
            if gw:
                LOG.debug("check external gateway %s on %s" % (gw, l3_host))
                cmd = "ip netns exec qrouter-%s ping -c 1 %s" % (rid, gw)
                out, err = ssh_connect(l3_host, cmd)
                if not err:
                    LOG.debug("external gateway is ok")
                else:
                    LOG.error("failed to connect external gateway on %s"
                              % (l3_host))
                if interface:
                    LOG.debug("check external interface %s qos on %s"
                              % (interface, l3_host))
                    cmd = ("ip netns exec qrouter-%s tc qdisc show dev %s"
                           % (rid, interface))
                    out, err = ssh_connect(l3_host, cmd)
                    if out:
                        LOG.debug("qos was found on external interface"
                                  " %s of qrouter-%s on %s"
                                  % (interface, rid, l3_host))
                    else:
                        LOG.error("qos was not found on external interface"
                                  " %s of qrouter-%s on %s"
                                  % (interface, rid, l3_host))
                else:
                    LOG.error("failed to get external interface of"
                              " qrouter-%s on %s" % (rid, l3_host))
            else:
                LOG.error("failed to get external gateway on %s" % (l3_host))
        else:
            LOG.debug('this port is normal port, do not need to check gateway')

def vrouter_check_one(rid):
    cmd = 'neutron router-port-list %s -f csv -F id -F name' % (rid)
    out = run_command(cmd)
    ports = []
    if out:
        ports = csv2dict(out)

    l3_host = vrouter_get_l3_host(rid)
    if l3_host:
        for port in ports:
            LOG.debug('start checking port %s[%s]' % (port['name'], port['id']))
            port_check_one(port['id'], l3_host)
            LOG.debug('finish checking port %s[%s]' % (port['name'], port['id']))
    # TODO: check dhcp?


def vrouter_get_l3_host(rid):
    cmd = "neutron l3-agent-list-hosting-router -f csv %s" \
          % (rid)
    out = run_command(cmd).strip('\r\n')
    if out:
        hosts = csv2dict(out)
        return hosts[0]['host']
    else:
        LOG.error('can not get l3 host for router %s' % (rid))
        return None


def _vrouter_check(parser):
    if parser.pid:
        port_check_one(parser.pid)
    elif parser.rid:
        vrouter_check_one(parser.rid)
    else:
        # 1) Get valid routers list
        cmd = 'neutron router-list -f csv -F id -F name'
        if parser.tid:
            cmd += ' --tenant-id %s' % (parser.tid)
        out = run_command(cmd)
        routers = []
        if out:
            routers = csv2dict(out)

        # 2) Check every router one by one: .e.g. status, ip address ..., this
        #    is done on neutron node which namespace belong to.
        # tenant ID
        for router in routers:
            LOG.info('start checking route %s[%s]' % (router['name'], router['id']))
            vrouter_check_one(router['id'])
            LOG.info('finish checking route %s[%s]' % (router['name'], router['id']))


def vrouter_check(parser):
    if NODE_ROLE.is_fuel():
        # TODO: run on fuel node on future
        LOG.error('This check can be run only on network node')
        return
        # pick one controller to run
        controller_node = None
        for node in NODE_ROLE.nodes:
            if node['roles'] == 'controller':
                controller_node = node['host']
        cmd = 'source /root/openrc;%s' % (' '.join(sys.argv))
        ssh_connect2(controller_node, cmd)
    elif NODE_ROLE.is_controller():
        _vrouter_check(parser)
    else:
        LOG.error('This check can be run only on network node')


def make_vrouter(parser):
    '''Check Neutron virtual router'''
    parser.add_argument(
        '--tid',
        help='Tenant ID',
    )
    parser.add_argument(
        '--pid',
        help='Port ID',
    )
    parser.add_argument(
        '--rid',
        help='Router ID',
    )
    parser.set_defaults(func=vrouter_check)

entry_points = [
    ('vrouter', make_vrouter),
]


def make_subcommand(parser):
    subp = parser.add_subparsers(
        title='Commands',
        metavar='COMMAND',
        help='DESCRIPTION',
        )

    for (name, fn) in entry_points:
        p = subp.add_parser(
            name,
            description=fn.__doc__,
            help=fn.__doc__,
        )
        fn(p)
    return parser


def make(parser):
    '''Check openstack network. e.g. virtual router'''
    return make_subcommand(parser)
