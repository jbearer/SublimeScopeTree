from inspect import getargspec
import logging
import sys

import SublimeScopeTree.lib.settings as settings

class FormatLogger(logging.LoggerAdapter):
    def __init__(self, logger, name):
        self.logger = logger
        self.name = name

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            self.logger._log(level, msg.format(*args, **kwargs), (),
                {key: kwargs[key] for key in getargspec(self.logger._log).args[1:] if key in kwargs})

def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(get_handler())
    logger.setLevel(log_level())
    return FormatLogger(logger, name)

def get_handler():
    handler = None
    filename = settings.get_setting('log_file', None)
    filename = filename or 'stdout'

    if filename == 'stdout':
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(filename)

    assert handler
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
    return handler

def log_level():
    levels = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'notset': logging.NOTSET
    }

    try:
        return levels[settings.get_setting('log_level', 'info')]
    except KeyError:
        return logging.NOTSET

def reset_log_file():
    filename = settings.get_setting('log_file', None)
    if filename:
        open(filename, 'w').close()

if settings.get_setting('reset_log', False):
    reset_log_file()

# Ugly, but it breaks the cyclic import
settings.init_logger(get_logger('lib.settings'))
