from SublimeScopeTree.lib.parse import Parser, register_parser_factory
from SublimeScopeTree.lib.test import test_only
from SublimeScopeTree.lib.tree import ScopeTree

class MockParser(Parser):
    def __init__(self, view):
        self._on_parse = None
        self._view = view

    def parse(self):
        if self._on_parse:
            return self._on_parse(self._view)
        else:
            return ScopeTree()

    @test_only
    def on_parse(self, callback):
        assert self._on_parse is None, 'Can only register one callback'
        self._on_parse = callback

def get_parser(view, instantiated={}):
    '''
    Get a mock parser for a given view. We cache the parsers which have been instantiated and only
    instantiate one parser for a given view. That way, the same parser gotten by the parse library
    can also be gotten and manipulated by unit tests.
    '''
    if view.id() not in instantiated:
        instantiated[view.id()] = MockParser(view)
    return instantiated[view.id()]

register_parser_factory('mock', get_parser)
