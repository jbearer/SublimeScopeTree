from unittest import TestCase
from os.path import dirname

from sublime import View, Region, active_window
import sublime_plugin

from SublimeScopeTree.lib.errors import ParserSyntaxError
from SublimeScopeTree.lib.log import get_logger
from SublimeScopeTree.lib.parse import parse
from SublimeScopeTree.lib.test import test, test_only, debug
from SublimeScopeTree.lib.tree import ScopeTree, Scope

log = get_logger('test.parser')

class scratch_view:
    @test_only
    def __init__(self, name='test.parser', syntax_file=dirname(__file__) + '/../mock.sublime-syntax', text=''):
        self.view = active_window().new_file()
        self.view.set_name(name)
        self.view.set_scratch(True)
        self.view.set_read_only(True)
        self.view.settings().set('syntax', syntax_file)
        self.view.run_command('scratch_view_set_text', {'text': text})

        log.debug('Created scratch view {name} ({id}):\n  syntax={syntax}\n  text={text}',
            name=name, id=self.view.id(), syntax=syntax_file, text=text)

    @test_only
    def __enter__(self):
        return self.view

    @test_only
    def __exit__(self, *_):
        active_window().focus_view(self.view)
        active_window().run_command("close")

@test_only
def syntax_file(syntax):
    return 'Packages/{syntax}/{syntax}.sublime-syntax'.format(syntax=syntax)

class Basic(TestCase):
    def setUp(self):
        self.supported_syntax = []

    @test
    def test_get_parser(self):
        with scratch_view() as view:
            from SublimeScopeTree.parsers.mock import get_parser
            parser = get_parser(view)

            parser_called = False
            def on_parse(view_to_parse):
                nonlocal parser_called

                self.assertEqual(view_to_parse, view)
                parser_called = True

            parser.on_parse(on_parse)
            parse(view)
            self.assertTrue(parser_called)

    @test
    def test_supported_syntax(self):
        '''
        Make sure we can import a parser, parse a view, and get a ScopeTree back with no errors.
        This is the most minimal test that a parser can pass.
        '''
        for syntax in self.supported_syntax:
            with scratch_view(syntax_file=syntax_file(syntax)) as view:
                self.assertEqual(parse(view), ScopeTree(view))

    @test
    def test_unsupported_syntax(self):
        syntax = 'unsupported'
        self.assertFalse(syntax in self.supported_syntax)
        with scratch_view(syntax_file=syntax_file(syntax)) as view:
            with self.assertRaises(ParserSyntaxError):
                parse(view)
