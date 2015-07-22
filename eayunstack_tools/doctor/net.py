from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.utils import ssh_connect2, NODE_ROLE
import commands
import json
import re
import sys


# TODO: move to utils.py?
def run_command(cmd):
    reval = None
    (status, out) = commands.getstatusoutput(cmd)
    if status != 0:
        LOG.error("run %s error: %s" % (cmd, out))
        reval = None
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


def port_check_one(pid):
    def port_log(device_owner, s):
        if device_owner == 'network:router_gateway':
            LOG.error(s)
        else:
            LOG.warn(s)

    cmd = 'neutron port-show %s -f json -F status -F admin_state_up '\
          '-F device_owner -F device_id' % (pid)
    out = run_command(cmd)
    if out:
        out = json.loads(out)
        detail = dict(map(lambda d: (d['Field'], d['Value']), out))

        # 1) check status of gateway port and interface port
        if detail['status'] != 'ACTIVE':
            port_log(detail['device_owner'], "status of port %s[%s] is down"
                     % (detail['device_owner'], pid))
        if not detail['admin_state_up']:
            port_log(detail['device_owner'], "admin_status of port %s[%s] is down"
                     % (detail['device_owner'], pid))

        # 2) ping external gateway to check network status
        if detail['device_owner'] == 'network:router_gateway':
            cmd = "ip netns exec qrouter-%s ip route show | "\
                  "grep 'default' | awk '{print $3}'" % (detail['device_id'])
            gw = run_command(cmd)
            if out:
                cmd = "ip netns exec qrouter-%s ping -c 1 %s"\
                      % (detail['device_id'], gw)
                LOG.debug("check external gateway")
                out = run_command(cmd)
                if out:
                    LOG.debug("external gateway is ok")
                else:
                    LOG.error("failed to connect external gateway")
            else:
                LOG.error("failed to get external gateway")


def vrouter_check_one(rid):
    cmd = 'neutron router-port-list %s -f csv -F id -F name' % (rid)
    out = run_command(cmd)
    ports = []
    if out:
        ports = csv2dict(out)

    for port in ports:
        LOG.debug('check port %s[%s]' % (port['name'], port['id']))
        port_check_one(port['id'])
    # TODO: check dhcp?


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
            cmd = "neutron l3-agent-list-hosting-router -f csv %s" \
                  % (router['id'])
            out = run_command(cmd)
            if out:
                hosts = csv2dict(out)
                if hosts:
                    # TODO: check admin_state_up and so on
                    l3_host = hosts[0]['host']
                    LOG.info('check route %s[%s] on host %s'
                             % (router['name'], router['id'], l3_host))
                    if LOG.enable_debug:
                        cmd = 'source /root/openrc;eayunstack --debug doctor '\
                              'net vrouter --rid %s' % (router['id'])
                    else:
                        cmd = 'source /root/openrc;eayunstack doctor '\
                              'net vrouter --rid %s' % (router['id'])
                    # TODO: if l3_host is localhost, do not ssh_connect2
                    ssh_connect2(l3_host, cmd)


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
