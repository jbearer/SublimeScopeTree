class FormattedError(Exception):
    def __init__(self, msg, *args, **kwargs):
        # We only want to call format if the client actually intended msg to be a format string. If
        # msg was not intended to be formatted, it may contain { and } characters, which can make
        # string.format complain.
        if args or kwargs:
            msg = msg.format(*args, **kwargs)

        Exception.__init__(self, msg)

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

class RenderError(FormattedError):
    def __init__(self, msg, *args, **kwargs):
        FormattedError.__init__(self, msg, *args, **kwargs)

class TestOnlyError(FormattedError):
    def __init__(self, func, caller):
        FormattedError.__init__(self, 'Test-only function {} called by production function {}', func, caller)

class ParserSyntaxError(FormattedError):
    def __init__(self, msg, *args, **kwargs):
        FormattedError.__init__(self, msg, *args, **kwargs)

class ParseError(FormattedError):
    def __init__(self, view, location, msg, *args, **kwargs):
        prefix = 'Parse error ({file}:{line}): '.format(file=view.filename(), line=view.line(location))
        FormattedError.__init__(self, prefix + msg, *args, **kwargs)
