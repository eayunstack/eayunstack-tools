import commands
import re

# get masters or slaves node list for rabbitmq cluster
def get_rabbitmq_nodes(role):
    if role not in ['masters', 'slaves']: return
    role = role.capitalize()
    (s, o) = commands.getstatusoutput('pcs status resources | grep %s' % role)
    if s != 0 or o is None:
        return
    else:
        p = re.compile(r'     %s: \[ (.+) \]' % role)
        m = p.match(o).groups()
        return m[0].split()

#print get_rabbitmq_nodes('slaves')
