from functools import wraps
import sys
import traceback

from lib.errors import TestOnlyError

test_funcs = set()

def test(func):
    '''
    Decorator to declare a function a unit test, capable of calling test_only functions
    '''
    test_funcs.add(func.__name__)
    return func

def test_only(func):
    '''
    Decorator to declare a function test_only. The function will cause a runtime error if not called
    (possibly indirectly) by a "test" decorated function
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Were we called by a test function?
        caller = traceback.extract_stack(limit=2)[0][2]
        if caller not in test_funcs:
            raise TestOnlyError(func.__name__, caller)
        return func(*args, **kwargs)

    # Test only functions can call other test only functions
    test_funcs.add(func.__name__)

    return wrapper

# We need these so nose doesn't "discover" these decorators
test.__name__ = '__test__'
test_only.__name__ = '__test_only__'

class MockHook():
    '''
    Import hook which will import test.mocks when one of the mocked out modules is requested.
    '''

    def __init__(self, modules):
        self.modules = modules

    def find_module(self, name, _=None):
        if name in self.modules:
            return self
        return None

    def load_module(self, name):
        if name not in sys.modules:
            import lib.mocks as mocks
            sys.modules[name] = mocks
        return sys.modules[name]

def mock(*modules):
    sys.meta_path.append(MockHook(modules))
