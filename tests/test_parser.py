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
        self.supported_syntax = ['C++']

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

class CppParser(TestCase):
    def view(self, *args, **kwargs):
        return scratch_view(syntax_file=syntax_file('C++'), *args, **kwargs)

    def run_test(self, source_code, *top_level_scopes):
        with self.view(text=source_code) as view:
            correct_tree = ScopeTree(view)
            correct_tree.set_top_level_scopes(*top_level_scopes)
            self.assertEqual(correct_tree, parse(view))

    def simple_test(self, source_code):
        '''
        Test a source file with a single scope named by the first line of the source code.
        '''
        self.run_test(source_code, Scope(Region(0, len(source_code)), source_code.split('\n')[0]))

    def simple_structure_test(self, kind, semicolon=False):
        source_code = \
'''{kind} test_{kind}
{{
    // Nothing going on here
}}{semicolon}'''.format(kind=kind, semicolon=';' if semicolon else '')

        self.simple_test(source_code)

    def simple_function_test(self, return_t):
        source_code = \
'''{return_t} foo()
{{
    int x = 0;
    while (x < 42) {{
        ++x;
    }}
    std::cout << "The answer is " << x << "!" << std::endl;
    return {return_t}{{0}};
}}'''.format(return_t=return_t)

        self.simple_test(source_code)

    def simple_function_declaration_test(self, return_t):
        self.simple_test('{return_t} foo();'.format(return_t=return_t))

    @test
    def test_class(self):
        self.simple_structure_test('class', semicolon=True)

    @test
    def test_struct(self):
        self.simple_structure_test('struct', semicolon=True)

    @test
    def test_namespace(self):
        self.simple_structure_test('namespace')

    @test
    def test_function_primitive(self):
        self.simple_function_test('int')

    @test
    def test_function_typedef(self):
        self.simple_function_test('typedef_t')

    @test
    def test_function_declaration_primitive(self):
        self.simple_function_declaration_test('int')

    @test
    def test_function_declaration_typedef(self):
        self.simple_function_declaration_test('typedef_t')

    @test
    def test_function_complex_return_type(self):
        self.simple_function_test('char const * const')

    @test
    def test_function_multiline(self):
        source_code = \
'''void
foo()
{
    int x = 0;
    while (x < 42) {{
        ++x;
    }}
    std::cout << "The answer is " << x << "!" << std::endl;
}'''

        self.run_test(source_code, Scope(Region(0, len(source_code)), 'void \\\nfoo()'))

    @test
    def test_function_declaration_multiline(self):
        source_code = \
'''virtual void an_extremely_long_function_name_with_many_parameters(int a, string b,
    std::unordered_map<int, string> const & c) const = 0;'''

        self.run_test(source_code, Scope(Region(0, len(source_code)), source_code.replace('\n', ' \\\n')))

    @test
    def test_nested_scopes(self):
        source_code = \
'''class my_class
{
public:
    my_class() = default;
private:
    void foo() {}
};'''

        my_class = Scope(Region(0, len(source_code)), 'class my_class')
        my_class.add_child(Scope(Region(source_code.index('my_class()'), source_code.index('\nprivate')),
                                 'my_class() = default;'))
        my_class.add_child(Scope(Region(source_code.index('void foo()'), source_code.index('\n};')),
                                 'void foo()'))
        self.run_test(source_code, my_class)

    @test
    def test_all_scope_types(self):

        # The /* End <thing> */ comments make it easy to parse this to generate the correct output.
        # See definition of scope(name) below.
        source_code = \
'''#include <iostream>

char * foo();/* End char * foo(); */

class my_class
{
public:
    my_class() : data(42) {}/* End my_class() */

    int get_data()
    {
        return helper();
    }/* End int get_data() */

    void defined_elsewhere();/* End void defined_elsewhere(); */

private:
    int helper()
    {
        return data;
    }/* End int helper() */

    int data;

};/* End class my_class */

void my_class::defined_elsewhere()
{
    // Do stuff
}/* End void my_class::defined_elsewhere() */

class my_derived_class
    : my_class
{
    void im_running_out_of_names()
    {
        // Do stuff
    }/* End void im_running_out_of_names() */
};/* End class my_derived_class */

struct my_struct
{
    struct inner_struct
    {
        void inner_struct_go() {
            // Do stuff
        }/* End void inner_struct_go() */
    };/* End struct inner_struct */
    int data;
    inner_struct * indirect_data;
};/* End struct my_struct */

namespace my_namespace {
    int data;
    void foo() {}/* End void foo() */
}/* End namespace my_namespace */

char *
foo()
{
    return "Hello world!";
}/* End char *\nfoo() */

int
main(int argc, char ** argv)
{
    std::cout << foo() << std::endl;
    return 0;
}/* End int\nmain(int argc, char ** argv) */
'''
        def scope(name):
            start = source_code.index(name)
            end = source_code.index('/* End {} */'.format(name))
            return Scope(Region(start, end), name.replace('\n', ' \\\n'))

        foo_declaration     = scope('char * foo();')
        my_class            = scope('class my_class')
        defined_elsewhere   = scope('void my_class::defined_elsewhere()')
        my_derived_class    = scope('class my_derived_class')
        my_struct           = scope('struct my_struct')
        my_namespace        = scope('namespace my_namespace')
        foo_definition      = scope('char *\nfoo()')
        main                = scope('int\nmain(int argc, char ** argv)')

        my_class.add_child(scope('my_class()'))
        my_class.add_child(scope('int get_data()'))
        my_class.add_child(scope('void defined_elsewhere();'))
        my_class.add_child(scope('int helper()'))

        my_derived_class.add_child(scope('void im_running_out_of_names()'))

        my_namespace.add_child(scope('void foo()'))

        inner_struct = scope('struct inner_struct')
        inner_struct.add_child(scope('void inner_struct_go()'))
        my_struct.add_child(inner_struct)

        self.run_test(source_code,
                      foo_declaration,
                      my_class,
                      defined_elsewhere,
                      my_derived_class,
                      my_struct,
                      my_namespace,
                      foo_definition,
                      main)
