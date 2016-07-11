from eayunstack_tools.utils import get_node_list
from eayunstack_tools.utils import bytes2human
from eayunstack_tools.sys_utils import ssh_connect2
import commands
import re
from eayunstack_tools.logger import StackLOG as LOG
from eayunstack_tools.doctor.utils import run_doctor_on_nodes


# get node list for rabbitmq cluster
def get_rabbitmq_nodes():
    running_nodes = []
    (s, o) = commands.getstatusoutput('rabbitmqctl -q cluster_status')
    if s == 0:
        p = re.compile('.*running_nodes,\[([^\]]+)\]', re.S)
        rns = p.findall(o)
        for rn in rns[0].split(','):
            node = rn.strip()
            pp = re.compile(r'\'rabbit@(.+)\'')
            mm = pp.match(node).groups()
            running_nodes.append(mm[0])
    return running_nodes



# get running node list for mysql cluster
def get_mysql_nodes():
    running_nodes = []
    (s, o) = commands.getstatusoutput('crm_resource --locate --resource clone_p_mysql 2> /dev/null | grep "running on"')
    if s != 0 or o is None:
        return
    else:
        for entry in o.split('\n'):
            running_nodes.append(entry.split()[5])
    return running_nodes

# get running node list for haproxy cluster
def get_haproxy_nodes():
    running_nodes = []
    (s, o) = commands.getstatusoutput('crm_resource --locate --resource clone_p_haproxy 2> /dev/null | grep "running on"')
    if s != 0 or o is None:
        return
    else:
        for entry in o.split('\n'):
            running_nodes.append(entry.split()[5])
    return running_nodes


# get ceph cluster status
def ceph_check_health():
    def _log(func, msg):
        func('Ceph cluster check faild !')
        # FIXME: cause the log module issue, need to send error msg line 
        # by line
        for l in msg.split('\n'):
            func(l)

    (s, o) = commands.getstatusoutput('ceph health')
    if s != 0:
        return
    else:
        if o == 'HEALTH_OK':
            LOG.info('Ceph cluster check successfully !')
        else:
            (ss, oo) = commands.getstatusoutput('ceph health detail')
            if o.startswith('HEALTH_WARN'):
                count = len(oo)
                if count > 150:
                    _log(LOG.warn, oo.splitlines()[0])
            else:
                count = len(oo)
                if count > 150:
                    _log(LOG.error, oo.splitlines()[0])


# get ceph osd status
def get_ceph_osd_status():
    (s, o) = commands.getstatusoutput('ceph osd tree')
    if s != 0 or o is None:
        return
    else:
        return o

# get ceph global space
def get_ceph_space():
    (s,o) = commands.getstatusoutput("ceph df | grep 'RAW USED' -A 1 | awk '{print $4}'")
    if s != 0 or o is None:
        return float(-1)
    else:
        space_use = float((o.split("USED\n"))[1])
        return space_use

# check all nodes
def check_all_nodes(check_obj):
    if check_obj is 'all':
        if LOG.enable_debug:
            check_cmd = 'sudo eayunstack --debug doctor cls --all'
        else:
            check_cmd = 'sudo eayunstack doctor cls --all'
    else:
        if LOG.enable_debug:
            check_cmd = 'sudo eayunstack --debug doctor cls -n %s' % check_obj
        else:
            check_cmd = 'sudo eayunstack doctor cls -n %s' % check_obj
    # get controller node list
    node_list = get_node_list('controller')
    # ssh to all controller node to check obj
    if len(node_list) == 0:
        LOG.warn('Node list is null !')
        return
    else:
        if check_obj == 'ceph':
            # only need to check one node for ceph cluster
            ceph_node = node_list[0]
            run_doctor_cmd_on_node('controller', ceph_node, check_cmd)
        else:
            nodes = []
            for node in node_list:
                node_info = {}
                node_info['role'] = 'controller'
                node_info['name'] = node
                nodes.append(node_info)
            result = run_doctor_on_nodes(nodes, check_cmd)
            for res in result:
                LOG.info(res, remote=True)

def get_crm_resource_list():
    resource_list = []
    (s, o) = commands.getstatusoutput('crm_resource -l')
    if s != 0 or o is None:
        return
    else:
        for entry in o.split('\n'):
            if ':' in entry:
                entry = entry.split(':')[0]
                entry = ('clone_' + entry, 'cp')
            else:
                entry = (entry, 'p')
            resource_list.append(entry)
        resource_list = list(set(resource_list))
    return resource_list

def get_crm_resource_running_nodes(resource):
    running_nodes = []
    (s, o) = commands.getstatusoutput('crm_resource --locate --resource %s 2> /dev/null | grep "running on"' % resource)
    if s != 0 or o is None:
        return
    else:
        for entry in o.split('\n'):
            running_nodes.append(entry.split()[5])
    return running_nodes

def csv2dict(csv):
    """Convert result format from csv to dict:
csv format:
# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,comp_in,comp_out,comp_byp,comp_rsp,lastsess,last_chk,last_agt,qtime,ctime,rtime,ttime,
Stats,FRONTEND,,,2,4,8000,85,2815007,864775742,0,0,20,,,,,OPEN,,,,,,,,,1,2,0,,,,0,1,0,4,,,,0,5319,0,20,0,0,,1,4,5340,,,0,0,0,0,,,,,,,,

dict format:
[{'status': 'OPEN', 'lastchg': '', 'weight': '', 'slim': '8000', 'pid': '1', 'comp_byp': '0', 'lastsess': '', 'rate_lim': '0', 'check_duration': '', 'rate': '1', 'req_rate': '1', 'check_status': '', 'econ': '', 'comp_out': '0', 'wredis': '', 'dresp': '0', 'ereq': '20', 'tracked': '', 'comp_in': '0', 'pxname': 'Stats', 'dreq': '0', 'hrsp_5xx': '0', 'last_chk': '', 'check_code': '', 'sid': '0', 'bout': '864775742', 'hrsp_1xx': '0', 'qlimit': '', 'hrsp_other': '0', 'bin': '2815007', 'rtime': '', 'smax': '4', 'req_tot': '5340', 'lbtot': '', 'stot': '85', 'wretr': '', 'req_rate_max': '4', 'ttime': '', 'iid': '2', 'hrsp_4xx': '20', 'chkfail': '', 'hanafail': '', 'downtime': '', 'qcur': '', 'eresp': '', 'comp_rsp': '0', 'cli_abrt': '', 'ctime': '', 'qtime': '', 'srv_abrt': '', 'throttle': '', 'last_agt': '', 'scur': '2', 'type': '0', 'bck': '', 'qmax': '', 'rate_max': '4', 'hrsp_2xx': '5319', 'act': '', 'chkdown': '', 'svname': 'FRONTEND', 'hrsp_3xx': '0'}]
    """
    field = csv.split('\n')[0]
    column = field.split(',')[:-1]
    column[0] = column[0].split(' ')[1]
    resource_list = []
    resources = csv.split('\n')[1:]
    for r in resources:
        resource = {}
        r = r.split(',')[:-1]
        if len(r) != len(column):
            continue
        index = 0
        for index in range(len(column)):
           resource[column[index]] = r[index]
        resource_list.append(resource)
    return resource_list

def get_rabbitmq_queues_list():
    queues_list = []
    (status, out) = commands.getstatusoutput('rabbitmqctl list_queues name '
                                             'messages memory | '
                                             'grep -v "Listing queues ..."'
                                             ' | grep -v "...done."')
    if status == 0:
        queues = out.split('\n')
        for queue in queues:
            queue_info = {}
            q = queue.split('\t')
            queue_info['name'] = q[0]
            queue_info['messages'] = q[1]
            queue_info['memory'] = q[2]
            queues_list.append(queue_info)

    return queues_list

def check_rabbitmq_queues(except_queues=None):
    messages_warn_limit = 100
    # unit: Byte
    memory_warn_limit = 1048576
    queues_list = get_rabbitmq_queues_list()
    for queue in queues_list:
        if int(queue['messages']) > messages_warn_limit \
            or int(queue['memory']) > memory_warn_limit:
            if except_queues and queue['name'] in except_queues:
                continue
            (mem_size, mem_unit) = bytes2human(int(queue['memory']))
            LOG.warn("Queue %s has %s messages and has been used %s %s memory."
                     % (queue['name'], queue['messages'], mem_size, mem_unit))
