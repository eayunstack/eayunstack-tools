import ConfigParser
import re
import MySQLdb
from eayunstack_tools.logger import StackLOG as LOG

class Stack_DB():
    def __init__(self, component):
        self.component = component

    def get_db_info(self):
        db_info = {}
        try:
            cp = ConfigParser.ConfigParser()
            cp.read(get_conf_file(self.component))
            if self.component == 'glance':
                value = cp.get('database', 'sql_connection')
            else:
                value = cp.get('database', 'connection')
            p = re.compile(r'mysql://(.+):(.+)@(.+)/(.+)\?(.+)')
            m = p.match(value).groups()
            db_info['username'] = m[0]
            db_info['password'] = m[1]
            db_info['hostname'] = m[2]
            db_info['database'] = m[3]
            return db_info
        except:
            LOG.error('Can not get db info from %s.' % get_conf_file(self.component))

    def connect(self, sql):
        db_info = self.get_db_info()
        try:
            conn = MySQLdb.connect(db_info['hostname'],
                                 db_info['username'],
                                 db_info['password'],
                                 db_info['database'])
            cursor = conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchall()
            cursor.close()
            conn.commit()
            conn.close()
            return result
        except MySQLdb.Error, e:
            try:
                sqlError = "Error %d:%s" % (e.args[0], e.args[1])
                LOG.error(sqlError)
            except IndexError:
                LOG.error("MySQL Error:%s" % str(e))
            
def get_conf_file(component):
    suffix = '.conf'
    if component == 'glance':
        suffix = '-api.conf'
    conf_file = '/etc/%s/%s%s' % (component, component, suffix)
    return conf_file 
