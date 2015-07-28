import logging
import sys
import StringIO
import commands
import re

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

COLORS = {
    'WARNING': YELLOW,
    'INFO': GREEN,
    'DEBUG': WHITE,
    'CRITICAL': RED,
    'ERROR': RED
}

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

BASE_COLOR_FORMAT = "[ %(color_levelname)-17s] %(message)s"
BASE_FORMAT = "%(asctime)s [%(name)s][%(levelname)-6s] %(message)s"


def color_message(message):
    message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    return message


class ColoredFormatter(logging.Formatter):
    """
    A very basic logging formatter that not only applies color to the levels of
    the ouput but will also truncate the level names so that they do not alter
    the visuals of logging when presented on the terminal.
    """

    def __init__(self, msg):
        # We do not need to know the year, month, day
        logging.Formatter.__init__(self, msg, datefmt='%H:%M:%S')

    def format(self, record):
        levelname = record.levelname
        truncated_level = record.levelname[:6]
        if levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + \
                truncated_level + RESET_SEQ
            record.color_levelname = levelname_color
        return logging.Formatter.format(self, record)


def color_format():
    """
    Main entry point to get a colored formatter, it will use the
    BASE_FORMAT by default.
    """
    color_fmt = color_message(BASE_COLOR_FORMAT)
    return ColoredFormatter(color_fmt)


class _StackLOG(object):
    def __init__(self):
        self.log_file = None
        self._enable_debug = False
        self._email_address = None
        self._email_buffer = None

    def setLevel(self, level):
        if self.log_file:
            pass
        else:
            self.logger.setLevel(level)

    def open(self, filename=None, debug=False, email_address=None):
        if filename:
            self.log_file = open(filename, 'a')
        else:
            self.log_file = None
            self.logger = logging.getLogger()
            self.logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(color_format())
            self.logger.addHandler(ch)
        self._enable_debug = debug
        if email_address:
            self._email_address = email_address
            self._email_buffer = StringIO.StringIO()

    def close(self):
        if self.log_file:
            self.log_file.close()
        if self._email_address:
            # If some error occurs, send it
            if self._email_buffer.getvalue():
                self._send_email()
            self._email_buffer.close()

    def _send_email(self):
        # TODO: get sender address from config file
        # TODO: check ssmtp?
        # TODO: using python smtp module to send email
        _email = """Date: Thursday, July 23, 2015 at 10:42:47 AM
From: eayunstack <eayunstack@163.com>
To: %s <%s>
Subject: mail from: eayunstack
MIME-Version: 1.0
Content-Type: text/plain; charset=ISO-8859-1
Content-Transfer-Encoding: 8bit

%s
""" % (self._email_address, self._email_address, self._email_buffer.getvalue())

        # TODO: Using random filename?
        with open('/tmp/email.txt', 'w') as f:
            f.write(_email)
            f.flush()
            cmd = 'ssmtp -t < /tmp/email.txt'
            self.info("Send email to %s" % self._email_address)
            (status, out) = commands.getstatusoutput(cmd)
            if status != 0:
                self.error("Send email failed: %s" % out)

    def info(self, msg, remote=False):
        if self.log_file:
            self.log_file.write(msg)
        else:
            if remote:
                for l in msg.split('\n'):
                    p = re.compile(r'\[(.*)\] (.*)')
                    if p.match(l):
                        level = p.match(l).groups()[0]
                        msg = p.match(l).groups()[1]
                        if 'INFO' in level:
                            self.logger.info(msg)
                        if 'DEBUG' in level:
                            self.debug(msg)
                        if 'WARN' in level:
                            self.warn(msg)
                        if 'ERROR' in level:
                            self.error(msg)
                    else:
                        print l
            else:
                self.logger.info(msg)

    @property
    def enable_debug(self):
        return self._enable_debug

    def debug(self, msg):
        if self._enable_debug:
            if self.log_file:
                self.log_file.write(msg)
            else:
                self.logger.debug(msg)

    def warn(self, msg):
        if self._email_buffer:
            _msg = "[ WARNING ] %s\n" % (msg.strip('\n'))
            self._email_buffer.write(_msg)
        if self.log_file:
            self.log_file.write(msg)
        else:
            self.logger.warn(msg)

    def error(self, msg):
        # do some decoration :)
        if self._email_buffer:
            _msg = "[ ERROR ] %s\n" % (msg.strip('\n'))
            self._email_buffer.write(_msg)
        if self.log_file:
            self.log_file.write(msg)
        else:
            self.logger.error(msg)

StackLOG = _StackLOG()


def fmt_print(msg):
    fmt = ' ' * 10
    print '%s%s' % (fmt, msg)


def fmt_msg(msg):
    fmt = ' ' * 10
    return '%s%s' % (fmt, msg)


def valid_print(key, value):
    fmt_print('%-40s: %s' % (key, value))


def fmt_excep_msg(exc):
    if str(exc):
        return '%s: %s\n' % (exc.__class__.__name__, exc)
    else:
        return '%s\n' % (exc.__class__.__name__)
