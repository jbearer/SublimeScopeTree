from itertools import permutations
from unittest import TestCase

from sublime import Region, View

from SublimeScopeTree.lib.tree import ScopeTree, Scope
from SublimeScopeTree.lib.errors import ScopeIntersectError, DuplicateScopeError, RenderError
from SublimeScopeTree.lib.settings import get_setting
from SublimeScopeTree.lib.test import test, test_only, debug, inject_settings
from SublimeScopeTree.lib.log import get_logger

log = get_logger('test.tree')

class MockView(View):
    @test_only
    def __init__(self, size):
        self._size = size

    def size(self):
        return self._size

@test_only
def test_view():
    return MockView(10000)

@test_only
def simulate_insert(*top_level_scopes):
    ScopeTree(test_view()).set_top_level_scopes(*top_level_scopes)

@test_only
def center(region):
    return (region.begin() + region.end()) / 2

class SetTopLevelScopes(TestCase):
    '''
    This helper function is used throughout the reset of the tests in this file, and it is assumed
    to be correct. Therefore, it deserves a test of its own.
    Note: pretty much the entire purpose of this test is to catch regressions.
    '''
    @test
    def test(self):
        tree = ScopeTree(test_view())

        root1 = Scope(Region(0, 10), 'root1')
        child1a = Scope(Region(1, 5), 'child1a')
        child2a = Scope(Region(6, 9), 'child2a')
        child3a = Scope(Region(2, 4), 'child3a')
        child4a = Scope(Region(7, 8), 'child4a')
        root2 = Scope(Region(20, 30), 'root2')
        child1b = Scope(Region(21, 25), 'child1b')
        child2b = Scope(Region(26, 29), 'child2b')
        child3b = Scope(Region(22, 24), 'child3b')
        child4b = Scope(Region(27, 28), 'child4b')

        root1.add_child(child1a)
        root1.add_child(child2a)
        child1a.add_child(child3a)
        child2a.add_child(child4a)
        root2.add_child(child1b)
        root2.add_child(child2b)
        child1b.add_child(child3b)
        child2b.add_child(child4b)

        tree.set_top_level_scopes(root1, root2)

        self.assertEqual(tree.size(), 10)

        self.assertEqual(root1.display_region(), Region(0, 62))
        self.assertEqual(child1a.display_region(), Region(6, 34))
        self.assertEqual(child2a.display_region(), Region(34, 62))
        self.assertEqual(child3a.display_region(), Region(18, 34))
        self.assertEqual(child4a.display_region(), Region(46, 62))
        self.assertEqual(root2.display_region(), Region(62, 124))
        self.assertEqual(child1b.display_region(), Region(68, 96))
        self.assertEqual(child2b.display_region(), Region(96, 124))
        self.assertEqual(child3b.display_region(), Region(80, 96))
        self.assertEqual(child4b.display_region(), Region(108, 124))

class Find(TestCase):
    def setUp(self):
        log.debug('Setting up test.test_tree.Find.')
        with debug():
            self.tree = ScopeTree(test_view())

    @test
    def test_empty(self):
        self.assertFalse(self.tree.find(0))

    @test
    def test_root_only(self):
        root = Scope(Region(0, 10), 'root')
        self.tree.set_top_level_scopes(root)

        self.assertEqual(self.tree.find(center(root.display_region())), root.display_region())
        self.assertFalse(self.tree.find(root.display_region().end() + 1))

    @test
    def test_breadth(self):
        root = Scope(Region(0, 10), 'root')
        children = [
            Scope(Region(1, 3), 'child1'),
            Scope(Region(4, 6), 'child2'),
            Scope(Region(7, 9), 'child3')
        ]
        for child in children:
            root.add_child(child)

        self.tree.set_top_level_scopes(root)

        self.assertEqual(self.tree.find(root.display_region().begin()), root.display_region())
        for child in children:
            self.assertEqual(child.display_region(), self.tree.find(center(child.display_region())))

    @test
    def test_depth(self):
        root = Scope(Region(0, 10), 'root')
        child1 = Scope(Region(1, 9), 'child1')
        child2 = Scope(Region(2, 8), 'child2')
        root.add_child(child1)
        child1.add_child(child2)
        self.tree.set_top_level_scopes(root)

        self.assertEqual(self.tree.find(root.display_region().begin()), root.display_region())
        self.assertEqual(self.tree.find(child1.display_region().begin()), child1.display_region())
        self.assertEqual(self.tree.find(center(child2.display_region())), child2.display_region())

    @test
    def test_multiple_roots(self):
        roots = [
            Scope(Region(0, 2), 'root1'),
            Scope(Region(3, 5), 'root2'),
            Scope(Region(8, 10), 'root3')
        ]
        self.tree.set_top_level_scopes(roots)
        for scope in roots:
            self.assertEqual(scope.display_region(), self.tree.find(center(scope.display_region())))

    @test
    def test_multiple_roots_depth(self):
        root1 = Scope(Region(0, 5), 'root1')
        root2 = Scope(Region(10, 15), 'root2')

        child1 = Scope(Region(1, 4), 'child1')
        root1.add_child(child1)
        child2 = Scope(Region(11, 14), 'child2')
        root2.add_child(child2)

        self.tree.set_top_level_scopes(root1, root2)

        self.assertEqual(root1.display_region(), self.tree.find(root1.display_region().begin() + 1))
        self.assertEqual(root2.display_region(), self.tree.find(root2.display_region().begin() + 1))
        self.assertEqual(child1.display_region(), self.tree.find(center(child1.display_region())))
        self.assertEqual(child2.display_region(), self.tree.find(center(child2.display_region())))

class Insert(TestCase):
    def setUp(self):
        log.debug('Setting up test.test_tree.Insert.')
        with debug():
            self.tree = ScopeTree(test_view())

    @test
    def test_empty(self):
        region = Region(0, 3)
        name = 'TEST REGION'
        node = Scope(region, name)

        self.assertEqual(self.tree.size(), 0)
        self.assertFalse(self.tree.find(center(region)))

        self.tree.insert(region, name)
        self.tree.render()

        simulate_insert(node)

        self.assertEqual(self.tree.size(), 1)
        self.assertEqual(node.display_region(), self.tree.find(center(region)))

    @test
    def test_one_child(self):
        root = (Region(1, 5), 'root')
        child = (Region(3, 4), 'child')

        # Make stuff happen in the tree
        self.tree.insert(*root)
        self.tree.insert(*child)
        self.tree.render()

        # Simulate what should happen internally with the tree's nodes
        root_node = Scope(*root)
        child_node = Scope(*child)
        root_node.add_child(child_node)
        simulate_insert(root_node)

        self.assertEqual(self.tree.size(), 2)
        self.assertEqual(child_node.display_region(), self.tree.find(center(child_node.display_region())))
        self.assertEqual(root_node.display_region(), self.tree.find(root_node.display_region().begin()))

    @test
    def test_breadth(self):
        root = (Region(0, 10), 'root')
        child1 = (Region(1, 5), 'child1')
        child2 = (Region(6, 9), 'child2')

        # Make stuff happen in the tree
        self.tree.insert(*root)
        self.tree.insert(*child1)
        self.tree.insert(*child2)
        self.tree.render()

        # Simulate what should happen internally with the tree's nodes
        root_node = Scope(*root)
        child1_node = Scope(*child1)
        child2_node = Scope(*child2)
        root_node.add_child(child1_node)
        root_node.add_child(child2_node)
        simulate_insert(root_node)

        self.assertEqual(self.tree.size(), 3)
        self.assertEqual(self.tree.find(root_node.display_region().begin()), root_node.display_region())
        self.assertEqual(self.tree.find(center(child1_node.display_region())), child1_node.display_region())
        self.assertEqual(self.tree.find(center(child2_node.display_region())), child2_node.display_region())

    @test
    def test_depth(self):
        root = (Region(0, 10), 'root')
        child1 = (Region(1, 5), 'child1')
        child2 = (Region(2, 4), 'child2')

        # Make stuff happen in the tree
        self.tree.insert(*root)
        self.tree.insert(*child1)
        self.tree.insert(*child2)
        self.tree.render()

        # Simulate what should happen internally with the tree's nodes
        root_node = Scope(*root)
        child1_node = Scope(*child1)
        child2_node = Scope(*child2)
        root_node.add_child(child1_node)
        child1_node.add_child(child2_node)
        simulate_insert(root_node)

        self.assertEqual(self.tree.size(), 3)
        self.assertEqual(self.tree.find(root_node.display_region().begin()), root_node.display_region())
        self.assertEqual(self.tree.find(child1_node.display_region().begin()), child1_node.display_region())
        self.assertEqual(self.tree.find(center(child2_node.display_region())), child2_node.display_region())

    @test
    def test_multiple_roots(self):
        roots = [
            (Region(0, 2), 'root1'),
            (Region(3, 5), 'root2'),
            (Region(8, 10), 'root3')
        ]
        for scope in roots:
            self.tree.insert(*scope)
        self.tree.render()

        roots = [Scope(*params) for params in roots]
        simulate_insert(roots)

        self.assertEqual(self.tree.size(), len(roots))
        for scope in roots:
            self.assertEqual(scope.display_region(), self.tree.find(center(scope.display_region())))

    @test
    def test_multiple_roots_depth(self):
        root1 = (Region(0, 5), 'root1')
        root2 = (Region(10, 15), 'root2')
        child1 = (Region(1, 4), 'child1')
        child2 = (Region(11, 14), 'child2')

        # Make stuff happen in the tree
        self.tree.insert(*root1)
        self.tree.insert(*root2)
        self.tree.insert(*child1)
        self.tree.insert(*child2)
        self.tree.render()

        # Simulate what should happen internally with the tree's nodes
        root1 = Scope(*root1)
        root2 = Scope(*root2)
        child1 = Scope(*child1)
        child2 = Scope(*child2)
        root1.add_child(child1)
        root2.add_child(child2)
        simulate_insert(root1, root2)

        self.assertEqual(root1.display_region(), self.tree.find(root1.display_region().begin() + 1))
        self.assertEqual(root2.display_region(), self.tree.find(root2.display_region().begin() + 1))
        self.assertEqual(child1.display_region(), self.tree.find(center(child1.display_region())))
        self.assertEqual(child2.display_region(), self.tree.find(center(child2.display_region())))

    @test
    def test_permutations(self):
        nodes = [
            (Region(0, 5), 'root1'),
            (Region(10, 15), 'root2'),
            (Region(1, 2), 'child1a'),
            (Region(3, 4), 'child1b'),
            (Region(11, 14), 'child2a'),
            (Region(12, 13), 'child2b')
        ]

        root1 = Scope(*nodes[0])
        root2 = Scope(*nodes[1])
        root1.add_child(Scope(*nodes[2]))
        root1.add_child(Scope(*nodes[3]))
        root2.add_child(Scope(*nodes[4]))
        root2.children[0].add_child(Scope(*nodes[5]))
        out_tree = self.tree
        out_tree.set_top_level_scopes(root1, root2)

        for permutation in permutations(nodes):
            log.info('Begin permutation test:\n{}', permutation)
            self.tree.set_top_level_scopes()
            for node in permutation:
                self.tree.insert(*node)
            self.tree.render()
            self.assertEqual(self.tree, out_tree)

    @test
    def test_invalid(self):
        root = Scope(Region(1, 5), 'root')
        self.tree.insert(root.source_region(), root.name)

        # Should raise an error if we try to find before updating
        with self.assertRaises(RenderError):
            self.tree.find(center(root.display_region()))

        self.tree.render()
        simulate_insert(root)
        self.assertEqual(self.tree.find(center(root.display_region())), root.display_region())

        # A region that intersects the tree's region
        with self.assertRaises(ScopeIntersectError):
            self.tree.insert(Region(4, 6), 'intersect')

        # A duplicate region
        with self.assertRaises(DuplicateScopeError):
            self.tree.insert(root.source_region(), 'The name should\'nt matter')

        # Make sure nothing got inserted
        self.assertEqual(self.tree.size(), 1)

    @test
    def test_nested_invalid(self):
        root = Scope(Region(1, 5), 'root')
        child = Scope(Region(2, 4), 'child')
        self.tree.insert(root.source_region(), root.name)
        self.tree.insert(child.source_region(), child.name)

        # Insert a region which intersects a child of root
        with self.assertRaises(ScopeIntersectError):
            self.tree.insert(Region(
                child.source_region().end() - 1, child.source_region().end() + 1), 'intersect')

        # Insert a region that duplicates a child of root
        with self.assertRaises(DuplicateScopeError):
            self.tree.insert(child.source_region(), 'The name should\'nt matter')

class Render(TestCase):
    def setUp(self):
        log.debug('Setting up test.test_tree.Render.')
        with debug():
            self.tree = ScopeTree(test_view())

        self.tree.insert(Region(0, 10), 'root1')
        self.tree.insert(Region(1, 5), 'child1a')
        self.tree.insert(Region(6, 9), 'child2a')
        self.tree.insert(Region(2, 4), 'child3a')
        self.tree.insert(Region(7, 8), 'child4a')
        self.tree.insert(Region(20, 30), 'root2')
        self.tree.insert(Region(21, 25), 'child1b')
        self.tree.insert(Region(26, 29), 'child2b')
        self.tree.insert(Region(22, 24), 'child3b')
        self.tree.insert(Region(27, 28), 'child4b')

        self.rendered = \
'''root1
{indent}child1a
{indent}{indent}child3a
{indent}child2a
{indent}{indent}child4a
root2
{indent}child1b
{indent}{indent}child3b
{indent}child2b
{indent}{indent}child4b
'''

    @test
    def test_default_settings(self):
        log.debug('Rendered tree:\n{}', self.tree.render())
        log.debug('Correct tree:\n{}', self.rendered.format(indent=' '*get_setting('indent_width')))
        self.assertEqual(self.tree.render(), self.rendered.format(indent=' '*get_setting('indent_width')))

    @test
    def test_indent_width(self):
        new_indent = 2 * get_setting('indent_width')
        inject_settings(indent_width=new_indent)
        log.debug('Rendered tree:\n{}', self.tree.render())
        log.debug('Correct tree:\n{}', self.rendered.format(indent=' '*new_indent))
        self.assertEqual(self.tree.render(), self.rendered.format(indent=' '*new_indent))
