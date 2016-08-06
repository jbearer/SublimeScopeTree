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

def get_setting(key, default=None):
    # Environment variables override settings
    env = 'sublime_scope_tree_{}'.format(key)
    if env in os.environ:
        setting = os.environ[env]
        if log:
            log.info('Got setting {}={} from environment', key, setting)
        return setting

    # If no environment variable, try the settings file
    raw = load_settings('SublimeScopeTree.sublime-settings').get(key, default)
    setting = raw
    if type(raw) == type(''):
        setting = expand(raw)

    if log:
        if raw == default:
            log.info('Using default setting {} for {}.', setting, key)
        else:
            log.info('Got setting {}={}{}', key, setting,
                     '' if raw == setting else ', expanded from {}'.format(raw))

    return setting
