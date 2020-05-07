import logging
import logging.handlers
import os
import datetime
import logging.config
import uuid
import json
import sys
import traceback
import io

# import 這個才會有顏色
try:
    import curses
except ImportError:
    curses = None

logdir = os.path.join(os.path.dirname(__file__), 'logs')
# 每一次啟動爬蟲都會有獨立的 logid，當爬蟲用 multiprocess 時辨識用
logid = str(uuid.uuid4())[0:4]
now_str = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
logger = logging.getLogger(__name__)

if not os.path.exists(logdir):
    os.mkdir(logdir)


def _final_hook(exctype, value, tb):
    s = io.StringIO()
    traceback.print_exception(exctype, value, tb, file=s)
    s.write('Call stack:\n')
    frame = tb.tb_frame
    if frame:
        traceback.print_stack(frame, file=s)
    logger.error(s.getvalue())
    s.close()
    raise Exception


sys.excepthook = _final_hook


def _stderr_supports_color():
    if os.getenv('LOGZERO_FORCE_COLOR') == '1':
        return True
    if os.name == 'nt':
        return True
    if curses and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                return True
        except Exception:
            pass
    return False


def to_unicode(value):
    """
    Converts a string argument to a unicode string.
    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, str):
        return value
    if not isinstance(value, bytes):
        raise TypeError(
            "Expected bytes, unicode, or None; got %r" % type(value))
    return value.decode("utf-8")


def _safe_unicode(s):
    try:
        return to_unicode(s)
    except UnicodeDecodeError:
        return repr(s)


def code_to_chars(code):
    CSI = '\033['
    return CSI + str(code) + 'm'


class AnsiFore:
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    RESET = 39

    def __init__(self):
        for name in dir(self):
            if not name.startswith('_'):
                value = getattr(self, name)
                setattr(self, name, code_to_chars(value))


ForegroundColors = AnsiFore()


class LogFormatter(logging.Formatter):
    DEFAULT_FORMAT = _fmt = '%(color)s[%(levelname)s %(asctime)s ID:{} PID:%(process)d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s'.format(
        logid)
    DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    DEFAULT_COLORS = {
        logging.DEBUG: ForegroundColors.CYAN,
        logging.INFO: ForegroundColors.GREEN,
        logging.WARNING: ForegroundColors.YELLOW,
        logging.ERROR: ForegroundColors.RED
    }

    def __init__(self,
                 color=True,
                 fmt=DEFAULT_FORMAT,
                 datefmt=DEFAULT_DATE_FORMAT,
                 colors=DEFAULT_COLORS):
        logging.Formatter.__init__(self, datefmt=datefmt)

        self._fmt = fmt
        self._colors = {}
        self._normal = ''

        if color and _stderr_supports_color():
            self._colors = colors
            self._normal = ForegroundColors.RESET

    def format(self, record):
        try:
            message = record.getMessage()
            assert isinstance(message, str)
            record.message = message
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)

        record.asctime = self.formatTime(record, self.datefmt)

        if record.levelno in self._colors:
            record.color = self._colors[record.levelno]
            record.end_color = self._normal
        else:
            record.color = record.end_color = ''

        formatted = self._fmt % record.__dict__

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            lines = [formatted.rstrip()]
            lines.extend(
                _safe_unicode(ln) for ln in record.exc_text.split('\n'))
            formatted = '\n'.join(lines)
        return formatted.replace("\n", "\n    ")


def gen_file(name, debug=False, single_file=False):
    if debug or single_file:
        file_name = "{}.log".format(name)
        file_name = os.path.join(logdir, file_name)
    else:
        file_name = "{}_{}_{}.log".format(name, now_str, logid)
        file_name = os.path.join(logdir, file_name)
    return file_name


def dictConfig(name=None, level=logging.INFO, debug=False,
               single_file=False, loggers=None, maxBytes=10e9, backupCount=1, **kwargs):
    """
    debug/single_file
        如果不是debug/single_file 每次執行都會產生一個log file
    name
        file name, 如果沒有指定時，寫到 crawler.log
    level
        預設所有loggers都是相同level
    maxBytes and backupCount
        預設在debug 才有
        否則每次執行都會產生一個新的file 也就不需要了
    kwargs
        disable_existing_loggers
            True 取消其他之前 init 的loggers
    """
    if not debug:
        maxBytes = 0
        backupCount = 0

    disable_existing_loggers = kwargs.get('disable_existing_loggers', False)
    level_dict = {}
    for key in dir(logging):
        val = getattr(logging, key)
        if isinstance(key, str) and key.lower() in "debug warning warn info error".split():
            if not callable(val):
                level_dict[val] = key
    level_str = level_dict.get(level, 'INFO')

    if name:
        file_name = gen_file(name, debug, single_file)
        file_handler = {
            'filename': file_name,
            'formatter': 'mono_color',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': maxBytes,
            'backupCount': backupCount
        }
    else:
        file_handler = {
            'filename': os.path.join(logdir, 'crawler.log'),
            'formatter': 'mono_color',
            'class': 'logging.handlers.WatchedFileHandler'
        }
    base_config = {
        'version': 1,
        'disable_existing_loggers': disable_existing_loggers,
        'formatters': {
            'standard': {
                '()': LogFormatter
            },
            'mono_color': {
                'format': '[%(levelname)s %(asctime)s ID:{} PID:%(process)d %(name)s %(module)s:%(lineno)d] %(message)s'.format(
                    logid)
            },
        },
        'handlers': {
            'file_handler': file_handler,
            'error_handler': {
                'formatter': 'mono_color',
                'class': 'logging.handlers.WatchedFileHandler',
                'level': 'WARNING',
                'filename': os.path.join(logdir, 'crawler.err')
            },
            'stream_handler': {
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'root': {
            'handlers': ['file_handler', 'stream_handler', 'error_handler'],
            'level': level_str
        },
        'loggers': {
            'django.request': {
                'handlers': ['file_handler', 'stream_handler', 'error_handler'],
                'level': logging.INFO,
                'propagate': True
            },
            'django': {
                'handlers': ['file_handler', 'stream_handler', 'error_handler'],
                'level': logging.INFO,
                'propagate': True
            },
            'requests': {
                'level': logging.WARNING,
                'propagate': True
            },
            'elasticsearch': {
                'level': logging.WARNING,
                'propagate': True
            },
            'chardet': {
                'level': logging.WARNING,
                'propagate': True
            },
            'urllib3': {
                'level': logging.INFO,
                'propagate': True
            }
        }
    }

    logging.config.dictConfig(base_config)
    return base_config


def setup_logger(*args, **kwargs):
    '''
    有人用這個函式嗎？
    '''
    pass


def set_config(config):
    '''
    change log config at runtime
    '''
    if 'version' not in config:
        config['version'] = 1
    if 'disable_existing_loggers' not in config and 'incremental' not in config:
        config['incremental'] = True
    if config is not None:
        logging.config.dictConfig(config)


def initlog(logfile=None, logdir=None, level=logging.INFO,
            maxBytes=10e9, backupCount=1, debug=False,
            **kwargs
            ):
    """
    參考dictConfig config={...} 可以更改default init方式
    預設會從現在工作目錄載入 log.json
    依下列順序載入 log 設定:
        ~/etc/log.json
        ~/etc/log-NAME.json
        ./log.json
    範例：
        {
                "loggers": {
                        "price_range": "DEBUG"
                }
        }
    這樣就可以針對 price_range debug，卻不會噴一堆 debug 訊息
    """
    if not logdir:
        logdir = os.path.join(os.environ['HOME'], 'var/log')
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    base_config = dictConfig(name=logfile, level=level, debug=debug,
                             maxBytes=maxBytes, backupCount=backupCount, **kwargs)
    other_config = kwargs.get('config', None)
    if 'config' in kwargs and kwargs['config']:
        set_config(kwargs.get('config'))

    config_orders = [os.path.join(os.environ['HOME'], 'etc', 'log.json')]
    if logfile:
        config_orders.append(os.path.join(os.environ['HOME'], 'etc', 'log-' + logfile + '.json'))
    config_orders.append('log.json')

    for f in config_orders:
        if os.path.exists(f):
            try:
                with open(f) as fd:
                    conf = json.load(fd)
                    set_config(conf)
            except Exception as e:
                print(e)
    return base_config


def getLogger(ec_type=None, provide=None, name=None):
    print('getLogger will be removed.')
    dirname = os.path.dirname(__file__)
    logger_name = '.'.join(filter(None, [ec_type, provide, name]))
    return logging.getLogger(logger_name)


def save_sample(name, data, mode='w'):
    logdir = os.path.join(os.environ['HOME'], 'var/log')
    try:
        os.makedirs(logdir)
    except Exception as e:
        pass

    filename = os.path.join(logdir, name + '.%s' % datetime.datetime.now().strftime('%Y%m%d.%H%M%S'))
    with open(filename, mode) as fd:
        fd.write(data)
    return filename


if __name__ == '__main__':
    """
    output:
    [level date time ID:logid   PID:pid logger module_name:line_no] msg
    [INFO 2018-10-02 18:48:08 ID:0153 PID:16929 root log:374] test demo
    """
    initlog('kk', level=logging.INFO, config=dict(
        loggers={
            'test': {
                'level': logging.WARNING,
                'propagate': True
            },
        }
    ))
    logger = logging.getLogger()
    logger.info('test demo')
    lgr = getLogger('test')
    lgr.info('test sub')
