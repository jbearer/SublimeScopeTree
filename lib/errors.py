class TestOnlyError(Exception):
    def __init__(self, func, caller):
        self.func = func
        self.caller = caller

    def __repr__(self):
        return 'Test-only function {} called by production function {}'.format(self.func, self.caller)
