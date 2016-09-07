import itertools
import re

from SublimeScopeTree.lib.errors import ParseError, ScopeError
from SublimeScopeTree.lib.log import get_logger
from SublimeScopeTree.lib.parse import Parser, register_parser
from SublimeScopeTree.lib.tree import ScopeTree

from sublime import Region, CLASS_LINE_START, CLASS_LINE_END

log = get_logger('parsers.C++')

class CppParser(Parser):
    def __init__(self, view):
        Parser.__init__(self, view)
        self.tree = ScopeTree(view)
        self.view = view

    def parse(self):
        log.debug('Parsing view {} as C++', self.view.id())
        for scope in self.find_scopes():
            region, name = self.describe(scope)
            log.debug('Inserting region {} {}', name, region)
            try:
                self.tree.insert(region, name)
            except ScopeError as err:
                raise ParseError(self.view, region, repr(err))
        return self.tree

    def find_scopes(self):
        selector_types = [
            'meta.class',
            'meta.struct',
            'meta.namespace',
            'meta.function',
            'meta.method'
        ]

        for depth in itertools.count(1):
            # Asking for a single selector only gives us scopes of that type at the top level. To
            # get nested scopes, we have to generate a selector of the form '{type1} ... type{n}'
            # at every depth n. Furthermore, we have s^n of these selectors where s is the number
            # of types; ie 'meta.class meta.function' picks member functions, while
            # 'meta.class meta.class' picks nested classes. We thus take the set S x S x ... S,
            # where S is the set of selector types, and we join its elements to form the
            # comma-separated selector. We do this at increasing depth until we reach a depth which
            # has no more scopes.
            nested_selectors = ','.join([
                ' '.join(selector) for selector in itertools.product(selector_types, repeat=depth)
            ])
            log.debug('Searching depth {} with selector {}', depth, nested_selectors)

            count = 0
            for scope in self.view.find_by_selector(nested_selectors):
                count  += 1
                yield scope

            if count == 0:
                log.info('No scopes found at depth {}, returning.', depth)
                return
            else:
                log.info('Found {} scopes at depth {}.', count, depth)

    def describe(self, region):
        region = self.expand_to_scope(region)
        return region, self.extract_name(region)

    def expand_to_scope(self, region):
        if self.view.score_selector(region.begin(), 'meta.function,meta.method') > 0:
            # Sublime gives us a region starting from the name of the function, not the return type.
            # We need to expand backwards to get the full prototype. We stop looking when we get to:
            search_terms = '(' + '|'.join([
                r';',                           # The end of a previous declaration, class, etc.
                r'}',                           # The end of a previous function or namespace
                r'{',                           # The beginning of a containing, class, struct, etc.
                r'\*/',                         # The end of a multiline comment
                r'//.*',                        # A comment
                r'(^|\n)\s*#.*',                # A preprocessor directive
                r'(public|private|protected):', # An access specifier
            ]) + ')'

            # Eat all whitespace between the thing we matched and the start of the prototype
            eat_whitespace = r'[\s\n]*'

            # Our "backwards" search consists of finding all matches in forwards order and taking
            # the last one.
            log.debug('Back-searching for beginning of prototype {}',
                self.view.substr(self.view.line(region.begin())))
            matches = re.finditer(search_terms + eat_whitespace, self.view.substr(Region(0, region.begin())))

            # Find the location of the last match, or beginning of file if no matches.
            start = 0
            matched_string = ''
            for match in matches:
                start = match.end()
                matched_string = match.group()

            if matched_string:
                log.debug('Prototype back-search concluded with string "{}".', matched_string)

            # Now we have a region including the prototype. We need to expand forwards to include
            # the block, or the semicolon for a declaration.
            log.debug('Searching for function definition or end of declaration.')
            match = re.search(r';|{', self.view.substr(Region(region.begin(), self.view.size())))
            if not match:
                raise ParseError(self.view, region, 'Expected ; or {.')
            end = region.begin() + match.end()
            if match.group() == '{':
                end = self.view.extract_scope(end).end()

            return Region(start, end)
        else:
            region = self.view.extract_scope(region.begin())
            if self.view.substr(Region(region.end(), region.end() + 1)) == ';':
                return Region(region.begin(), region.end() + 1)
            else:
                return region

    def extract_name(self, region):
        # From the start of the declaration/prototype, scan forward looking for the end of the
        # statement or the start of a block. The capture groups indicate the last character that
        # should be part of the name. For example, we include the semicolon to indicate that the
        # scope is a declaration only.
        match = re.search(r'(;)|(){|([^:]):[^:]',
            self.view.substr(Region(region.begin(), self.view.size())))
        if not match:
            raise ParseError(self.view, region, 'Expected ;, {, or :.')
        groups = sum([0 if group is None else 1 for group in match.groups()])
        assert groups == 1, 'Matched {} subgroups. Expected exactly 1.'.format(groups)

        end = region.begin() + match.end(match.lastindex)
        name = self.view.substr(Region(region.begin(), end))
        name = name.strip()

        # We don't want to mess up the user's text wrapping, since the names might be very long.
        # However, since newlines in a ScopeTree typically indicate nested scopes, we'll make it
        # clear that the line is continuing by inserting a backslash.
        name = re.sub(r'\s*\n', ' \\\n', name)

        return name

register_parser('C++', CppParser)
