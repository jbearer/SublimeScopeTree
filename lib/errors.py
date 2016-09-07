from SublimeScopeTree.lib.log import get_logger

log = get_logger('lib.errors')

class SSTException(Exception):
    '''
    Base class for all SublimeScopeTree errors. Simple wrapper around the stdlib Exception which
    logs its error message when created.
    '''
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.log()

    def __repr__(self):
        return self.args[0]

    def log(self):
        log.error(repr(self))

class DetailException(SSTException):
    def __init__(self, msg, detailed_msg):
        self.detail = detailed_msg
        SSTException.__init__(self, msg)

    def log(self):
        log.error(self.detail)

class FormattedError(SSTException):
    '''
    Base class for an exception which takes a format string and arguments with which to format it.
    If no arguments are given (besides the format string) then the message is interpreted as a
    regular string (not a format string) and format is not called.
    '''
    def __init__(self, msg, *args, **kwargs):
        # We only want to call format if the client actually intended msg to be a format string. If
        # msg was not intended to be formatted, it may contain { and } characters, which can make
        # string.format complain.
        if args or kwargs:
            msg = msg.format(*args, **kwargs)

        SSTException.__init__(self, msg)

class ScopeError(FormattedError):
    '''
    Base exception indicating a ScopeTree that has been put in an invalid state.
    '''
    def __init__(self, msg, *scopes):
        formatted_scopes = [
            '{} {}'.format(scope.name, repr(scope.source_region())) for scope in scopes
        ]
        FormattedError.__init__(self, msg, *formatted_scopes)

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

class ParseError(DetailException):
    def __init__(self, view, region, msg, *args, **kwargs):
        if args or kwargs:
            msg = msg.format(*args, **kwargs)

        prefix = 'Parse error ({file}:{start}-{end}): '.format(
            file=view.file_name(),
            start=view.rowcol(region.begin())[0] + 1,
            end=view.rowcol(region.end())[0] + 1)

        detail_prefix = 'Parse error:\n  file={file}\n  region={region}\n  error='.format(
            file=view.file_name(), region=repr(region))

        DetailException.__init__(self, prefix + msg, detail_prefix + msg)
