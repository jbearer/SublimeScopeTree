from unittest import TestCase

from lib.tree import ScopeTree, Scope
from lib.errors import ScopeIntersectError, ScopeNestingError, DuplicateScopeError
from lib.settings import get_setting
from lib.mocks import Region, inject_settings
from lib.test import test
from lib.log import get_logger

log = get_logger('test.tree')

class Find(TestCase):
    @test
    def test_empty(self):
        tree = ScopeTree()
        self.assertFalse(tree.find(0))

    @test
    def test_root_only(self):
        tree = ScopeTree()
        root = Scope(Region(0, 10), 'root')
        tree.set_root(root)

        self.assertEqual(tree.find(root.display_region().center()), root.display_region())
        self.assertFalse(tree.find(root.display_region().end() + 1))

    @test
    def test_breadth(self):
        tree = ScopeTree()
        root = Scope(Region(0, 10), 'root')
        child1 = Scope(Region(1, 5), 'child1')
        child2 = Scope(Region(6, 9), 'child2')
        root.add_child(child1)
        root.add_child(child2)
        tree.set_root(root)

        self.assertEqual(tree.find(root.display_region().begin()), root.display_region())
        self.assertEqual(tree.find(child1.display_region().center()), child1.display_region())
        self.assertEqual(tree.find(child2.display_region().center()), child2.display_region())

    @test
    def test_depth(self):
        tree = ScopeTree()
        root = Scope(Region(0, 10), 'root')
        child1 = Scope(Region(1, 9), 'child1')
        child2 = Scope(Region(2, 8), 'child2')
        root.add_child(child1)
        child1.add_child(child2)
        tree.set_root(root)

        self.assertEqual(tree.find(root.display_region().begin()), root.display_region())
        self.assertEqual(tree.find(child1.display_region().begin()), child1.display_region())
        self.assertEqual(tree.find(child2.display_region().center()), child2.display_region())

class Insert(TestCase):
    @test
    def test_empty(self):
        tree = ScopeTree()
        region = Region(0, 3)
        name = 'TEST REGION'
        node = Scope(region, name)

        self.assertEqual(tree.size(), 0)
        self.assertFalse(tree.find(region.center()))
        tree.insert(region, name)
        self.assertEqual(tree.size(), 1)
        self.assertEqual(node.display_region(), tree.find(region.center()))

    @test
    def test_one_child(self):
        tree = ScopeTree()
        root = (Region(1, 5), 'root')
        child = (Region(3, 4), 'child')

        # Make stuff happen in the tree
        tree.insert(*root)
        tree.insert(*child)

        # Simulate what should happen internally with the tree's nodes
        root_node = Scope(*root)
        child_node = Scope(*child)
        root_node.add_child(child_node)

        self.assertEqual(tree.size(), 2)
        self.assertEqual(child_node.display_region(), tree.find(child_node.display_region().center()))
        self.assertEqual(root_node.display_region(), tree.find(root_node.display_region().begin()))

    @test
    def test_breadth(self):
        tree = ScopeTree()
        root = (Region(0, 10), 'root')
        child1 = (Region(1, 5), 'child1')
        child2 = (Region(6, 9), 'child2')

        # Make stuff happen in the tree
        tree.insert(*root)
        tree.insert(*child1)
        tree.insert(*child2)

        # Simulate what should happen internally with the tree's nodes
        root_node = Scope(*root)
        child1_node = Scope(*child1)
        child2_node = Scope(*child2)
        root_node.add_child(child1_node)
        root_node.add_child(child2_node)

        self.assertEqual(tree.size(), 3)
        self.assertEqual(tree.find(root_node.display_region().begin()), root_node.display_region())
        self.assertEqual(tree.find(child1_node.display_region().center()), child1_node.display_region())
        self.assertEqual(tree.find(child2_node.display_region().center()), child2_node.display_region())

    @test
    def test_depth(self):
        tree = ScopeTree()
        root = (Region(0, 10), 'root')
        child1 = (Region(1, 5), 'child1')
        child2 = (Region(2, 4), 'child2')

        # Make stuff happen in the tree
        tree.insert(*root)
        tree.insert(*child1)
        tree.insert(*child2)

        # Simulate what should happen internally with the tree's nodes
        root_node = Scope(*root)
        child1_node = Scope(*child1)
        child2_node = Scope(*child2)
        root_node.add_child(child1_node)
        child1_node.add_child(child2_node)

        self.assertEqual(tree.size(), 3)
        self.assertEqual(tree.find(root_node.display_region().begin()), root_node.display_region())
        self.assertEqual(tree.find(child1_node.display_region().begin()), child1_node.display_region())
        self.assertEqual(tree.find(child2_node.display_region().center()), child2_node.display_region())

    @test
    def test_invalid(self):
        tree = ScopeTree()
        root = Scope(Region(1, 5), 'root')
        tree.insert(root.source_region(), root.name)

        # A region that intersects the tree's region
        with self.assertRaises(ScopeIntersectError):
            tree.insert(Region(4, 6), 'intersect')

        # Region outside the tree's region
        with self.assertRaises(ScopeNestingError):
            tree.insert(Region(6, 7), 'outer')

        # A region containing the tree's region
        with self.assertRaises(ScopeNestingError):
            tree.insert(Region(0, 6), 'container')

        # A duplicate region
        with self.assertRaises(DuplicateScopeError):
            tree.insert(root.source_region(), 'The name should\'nt matter')
            print(tree)

    @test
    def test_nested_invalid(self):
        tree = ScopeTree()
        root = Scope(Region(1, 5), 'root')
        child = Scope(Region(2, 4), 'child')
        tree.insert(root.source_region(), root.name)
        tree.insert(child.source_region(), child.name)

        # Insert a region which intersects a child of root
        with self.assertRaises(ScopeIntersectError):
            tree.insert(Region(
                child.source_region().end() - 1, child.source_region().end() + 1), 'intersect')

        # Insert a region that duplicates a child of root
        with self.assertRaises(DuplicateScopeError):
            tree.insert(child.source_region(), 'The name should\'nt matter')

class Repr(TestCase):
    @test
    def setUp(self):
        self.tree = ScopeTree()
        self.tree.insert(Region(0, 10), 'root')
        self.tree.insert(Region(1, 5), 'child1')
        self.tree.insert(Region(6, 9), 'child2')
        self.tree.insert(Region(2, 4), 'child3')
        self.tree.insert(Region(7, 8), 'child4')

        self.rendered = \
'''root
{indent}child1
{indent}{indent}child3
{indent}child2
{indent}{indent}child4
'''

    @test
    def test_default_settings(self):
        self.assertEqual(repr(self.tree), self.rendered.format(indent=' '*get_setting('indent_width')))

    @test
    def test_indent_width(self):
        new_indent = 2 * get_setting('indent_width')
        inject_settings(indent_width=new_indent)
        self.assertEqual(repr(self.tree), self.rendered.format(indent=' '*new_indent))
