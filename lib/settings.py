import logging
import os

from sublime import load_settings

# This is ugly, but it breaks the cyclic dependency
log = None
def init_logger(logger):
    global log
    log = logger
    log.debug('Initialized settings logger {}', logger.name)

def expand(raw):
    return os.path.expandvars(raw)

def log_setting(msg, key=None, value=None, level=logging.INFO, cache={}, **kwargs):
    if log is None:
        # We won't get a log until logging is loaded, do nothing for now
        return

    if key in cache and cache[key] == value:
        # Don't log settings we've seen already
        return

    log.log(level, msg, key=key, value=value, **kwargs)
    cache[key] = value

def get_setting(key, default=None):
    # Environment variables override settings
    env = 'sublime_scope_tree_{}'.format(key)
    if env in os.environ:
        setting = os.environ[env]
        if log:
            log_setting('Got setting {key}={value} from environment', key=key, value=setting)
        return setting

    # If no environment variable, try the settings file
    raw = load_settings('SublimeScopeTree.sublime-settings').get(key, default)
    setting = raw
    if type(raw) == type(''):
        setting = expand(raw)

    if log:
        if raw == default:
            log_setting('Using default setting {value} for {key}.', value=setting, key=key)
        else:
            log_setting('Got setting {key}={value}{expanded}', key=key, value=setting,
                expanded='' if raw == setting else ', expanded from {}'.format(raw))

    return setting
