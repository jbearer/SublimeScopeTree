import os

from SublimeScopeTree.lib.errors import ParserSyntaxError
from SublimeScopeTree.lib.log import get_logger

log = get_logger('lib.parse')

_parser_factories = {}

def parse(view):
    '''
    Return a scope tree representing the source code in the given view
    '''
    return get_parser(view).parse()

def get_parser(view):
    import SublimeScopeTree.parsers

    syntax = get_syntax(view)
    log.info('Using syntax {} for view {}', syntax, view.id())
    if syntax not in _parser_factories:
        raise ParserSyntaxError('No parser for syntax {}', syntax)
    return _parser_factories[syntax](view)

def get_syntax(view):
    '''
    Determine the syntax used by a view
    '''
    syntax_file = os.path.basename(view.settings().get('syntax'))
    if syntax_file[-15:] != '.sublime-syntax':
        raise ParserSyntaxError('Unable to determine syntax for view: syntax file {} does not have .sublime-syntax extension', syntax_file)
    return syntax_file[:-15]

def register_parser(syntax, parser_t):
    def factory(view):
        assert get_syntax(view) == syntax
        return parser_t(view)
    register_parser_factory(syntax, factory)

def register_parser_factory(syntax, factory):
    assert syntax not in _parser_factories, 'Duplicate parser'
    _parser_factories[syntax] = factory

class Parser():
    '''
    API for a parser: return a ScopeTree object which represents the source code in the given view.
    '''
    def __init__(self, view):
        pass

    def parse(self):
        raise NotImplementedError('Derived class must implement parse')
