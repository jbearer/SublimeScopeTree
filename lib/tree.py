from bisect import bisect_left

from lib.errors import ScopeNestingError, ScopeIntersectError, DuplicateScopeError
from lib.settings import get_setting
from lib.test import test_only

from sublime import Region

class ScopeTree:
    '''
    The data structure representing the scope tree. Each level of the tree is a further nested level
    of scope. Each node is a region that exists at that level of scope. The tree supports insertion
    of new scopes from a source code region, and lookup of the region in the scratch view display
    which contains a given point (this is used for folding/unfolding regions in the output).
    '''

    def __init__(self):
        self._root = None

    def __repr__(self):
        return self._render(self._root)

    def size(self):
        return self._size(self._root)

    def insert(self, region, name):
        '''
        Insert a new node with the given region and identifier.
        '''
        child = Scope(region, name)

        if self._root is None:
            self._root = child
            return

        # No intersecting scopes
        if self._root.intersects(child, Scope.source_region):
            raise ScopeIntersectError(self._root, child)

        # Must be a sub-region of the overall tree
        if not self._root.contains(region, Scope.source_region):
            raise ScopeNestingError(self._root, child)

        parent = self._find(self._root, child, Scope.source_region)
        if parent.source_region() == child.source_region():
            raise DuplicateScopeError(parent, child)
        parent.add_child(child)

    def find(self, point):
        '''
        Return the smallest display region containing the given point, or None if no region contains
        the point.
        '''
        if self._root is None or not self._root.contains(point, Scope.display_region):
            return None
        return self._find(self._root, point, Scope.display_region).display_region()

    def _size(self, root):
        if root is None:
            return 0

        size = 1
        for child in root.children:
            size += self._size(child)
        return size

    def _find(self, root, key, region_func):
        '''
        Find the leaf region containing key (point or scope) in the tree rooted at root.
        Precondition: self contains key
        '''
        assert root.contains(key, region_func)

        index = root.find_child_containing(key, region_func)
        if index == -1:
            # Root is the smallest scope that still contains point
            return root

        return self._find(root.children[index], key, region_func)

    def _render(self, root):
        ret = repr(root)
        for child in root.children:
            ret += self._render(child)
        return ret

    @test_only
    def set_root(self, root):
        if not isinstance(root, Scope):
            raise TypeError('Root of tree must be of type Scope')
        self._root = root

class Scope():
    '''
    A node in the scope tree. The node maps a region in the source file to a scope name (such as a
    class declaration or a function prototype). Each node keeps a list of children (nested scope)
    which is sorted in the same order as the scopes appear in the source. Each node knows about its
    region in the source code, and its region when displayed to the user in a scratch view.
    '''

    def __init__(self, region, name, indent=0, offset=0):
        '''
        Create a new node with the given scope region. Offset is the position in the scratch view at
        which the node should start displaying itself and its children. Name should be the
        identifier of the scope, for example, a class declaration or a function signature.
        '''
        self.children = []
        self.name = name

        self._region = region
        self._offset = offset
        self._indent = indent

    def __lt__(self, other):
        # We handle scopes and points so we can use binary search to lookup a scope containing a
        # point or to find the insertion point of a new child scope
        if isinstance(other, Scope):
            # We compare to scopes when trying to find the place to insert a new scope, so here we
            # care about the corresponding region in the source code
            return self._lt_scope(other, Scope.source_region)
        else:
            # We compare to points when we're looking up a point in the display, so we can fold or
            # unfold the scope containing that point. Thus, we care about the display region
            return self._lt_point(other, Scope.display_region)

    def __eq__(self, other):
        if not isinstance(other, Scope):
            return False

        # We don't need to compare display regions; if the name and source regions are the same,
        # so will be the display regions.
        return self.name == other.name and self.source_region() == other.source_region()

    def __repr__(self):
        return ' '*self._indent*get_setting('indent_width') + self.name + '\n'

    def add_child(self, child):
        '''
        Add the given scope as a child of this one.
        '''

        # Validate the child
        if self.intersects(child, Scope.source_region):
            raise ScopeIntersectError(self, child)
        if not self.contains(child, Scope.source_region):
            raise ScopeNestingError(self, child)

        # Indent the child
        child._indent = self._indent + 1
        child._offset = self._offset + len(repr(self))

        index = self._find_child(child)
        self.children.insert(index, child)

    def find_child_containing(self, key, region_func):
        '''
        Find the index of the child containing key, or -1 if no such child.
        '''
        index = self._find_child(key)
        if index < len(self.children) and self.children[index].contains(key, region_func):
            return index
        else:
            return -1

    def source_region(self):
        '''
        Get the region in the source code represented by this node
        '''
        return self._region

    def display_region(self):
        '''
        Get the region in the scratch view that corresponds to this node
        '''
        start = self._offset
        end = self.children[-1].display_region().end() if self.children else start + len(repr(self))
        return Region(start, end)

    def intersects(self, other, region_func):
        # It's useful to define intersection a bit differently than the Sublime API. We define it as
        # overlapping but not containing. Obviously, two valid scopes can never intersect, they can
        # only be nested or disjoint. So this is used only as an error condition.
        return region_func(self).intersects(region_func(other)) and \
            not (self.contains(other, region_func) or other.contains(self, region_func))

    def contains(self, other, region_func):
        if isinstance(other, Scope):
            return region_func(self).contains(region_func(other))
        else:
            # Point
            return region_func(self).contains(other)

    def _lt_point(self, other, region_func):
        return region_func(self).end() < other

    def _lt_scope(self, other, region_func):
        if self.intersects(other, region_func):
            raise ScopeIntersectError(other, self)

        return region_func(self).end() < region_func(other).begin()

    def _find_child(self, key):
        return bisect_left(self.children, key)
