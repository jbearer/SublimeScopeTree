class ScopeError(Exception):
    def __init__(self, msg, *scopes):
        self.msg = msg
        self.scopes = scopes

    def __repr__(self):
        formatted_scopes = [
            '{} {}'.format(scope.name, repr(scope.source_region())) for scope in self.scopes
        ]

        return self.msg.format(*formatted_scopes)

class ScopeIntersectError(ScopeError):
    def __init__(self, scope1, scope2):
        super(ScopeIntersectError, self).__init__('Scope {} intersects scope {}.', scope1, scope2)

class ScopeNestingError(ScopeError):
    def __init__(self, parent_scope, child_scope):
        super(ScopeNestingError, self).__init__(
            'Parent scope {} does not contain child scope {}.', parent_scope, child_scope)

class DuplicateScopeError(ScopeError):
    def __init__(self, scope1, scope2):
        super(DuplicateScopeError, self).__init__(
            'Scope {} duplicates scope scope {}.', scope1, scope2)

class TestOnlyError(Exception):
    def __init__(self, func, caller):
        self.func = func
        self.caller = caller

    def __repr__(self):
        return 'Test-only function {} called by production function {}'.format(self.func, self.caller)
