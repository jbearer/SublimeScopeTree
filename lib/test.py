from functools import wraps
import os
import sys
import traceback

import sublime

from SublimeScopeTree.lib.errors import TestOnlyError

_allow_test_only = False

def test(func):
    '''
    Decorator to declare a function a unit test, capable of calling test_only functions
    '''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        module = self.__module__
        log = sys.modules[module].log
        log.debug('Begin {}.{}.{}.', module, self.__class__.__name__, func.__name__)
        try:
            with debug():
                func(self, *args, **kwargs)
        except Exception as err:
            log.error('Exception: {}', repr(err), exc_info=True)
            log.error('{}.{}.{} FAILED.', module, self.__class__.__name__, func.__name__)

            # Reraise so the test runner reports this test as failed
            raise

        log.debug('{}.{}.{} PASSED.', module, self.__class__.__name__, func.__name__)

    return wrapper

def test_only(func):
    '''
    Decorator to declare a function test_only. The function will cause a runtime error if not called
    (possibly indirectly) by a "test" decorated function
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _allow_test_only:
            caller = traceback.extract_stack(limit=2)[0][2]
            raise TestOnlyError(func.__name__, caller)
        return func(*args, **kwargs)

    return wrapper

class debug:
    '''
    Suspend test only errors while inside a debug block
    '''
    def __enter__(self):
        global _allow_test_only
        _allow_test_only = True

    def __exit__(self, *_):
        global _allow_test_only
        _allow_test_only = False

@test_only
def inject_settings(**kwargs):
    '''
    Convenience method for dynamically playing around with settings
    '''
    s = sublime.load_settings('SublimeScopeTree.sublime-settings')
    for key, value in kwargs.items():
        s.set(key, value)
