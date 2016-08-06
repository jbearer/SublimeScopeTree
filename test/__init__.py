from lib.test import mock, test, debug
from lib.mocks import inject_settings

mock('sublime')

with debug():
    inject_settings(
        log_level = 'debug'
    )

from lib.log import get_logger

log = get_logger('test')

log.debug('Begin unit tests.')
