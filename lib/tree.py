import re

from SublimeScopeTree.lib.display import DisplayRegion
from SublimeScopeTree.lib.errors import ScopeIntersectError, ScopeNestingError, DuplicateScopeError, RenderError
from SublimeScopeTree.lib.log import get_logger
from SublimeScopeTree.lib.settings import get_setting
from SublimeScopeTree.lib.test import test_only

from sublime import Region

log = get_logger('lib.tree')

class ScopeTree:
    '''
    The data structure representing the scope tree. Each level of the tree is a further nested level
    of scope. Each node is a region that exists at that level of scope. The tree supports insertion
    of new scopes from a source code region, and lookup of the region in the scratch view display
    which contains a given point (this is used for folding/unfolding regions in the output).
    '''

    def __init__(self, view):
        # Top level file scope
        self._root = FileScope(view, self)
        self._size = 0
        self._needs_render = True

    @test_only
    def __repr__(self):
        '''
        Display the tree with additional diagnostic information.
        '''
        # Calculate all of the display regions. Doing this and then printing diagnostic information
        # is doing a lot of extra work, which is why we only use this function in unit tests.
        self.render()

        def _repr(root):
            ret = repr(root)
            for child in root.children:
                ret += _repr(child)
            return ret

        return _repr(self._root)

    def __eq__(self, other):
        if not isinstance(other, ScopeTree):
            return False

        def eq(root, other_root):
            if len(root.children) != len(other_root.children):
                return False
            if not root.children:
                assert not other_root.children
                return True

            for index, child in enumerate(root.children):
                if child != other_root.children[index]:
                    return False
                if not eq(child, other_root.children[index]):
                    return False
            return True

        return eq(self._root, other._root)

    def render(self):
        def _render(root, offset):
            root.display_start(offset)
            ret = root.render()
            for child in root.children:
                ret += _render(child, offset + len(ret))
            root.display_stop(offset + len(ret) - 1)
            return ret

        ret = _render(self._root, 0)
        self._needs_render = False
        return ret

    def size(self):
        return self._size

    def insert(self, region, name):
        '''
        Insert a new node with the given region and identifier.
        '''
        def _insert(root, child):
            log.info('Inserting {} as a descendant of {}', child, root)

            assert root
            children, index = root.children, root.find_child(child, Scope.source_region)
            if index < len(children):
                log.info('Insertion point is in place of {} at position {}.', children[index], index)
                if children[index].source_region() == child.source_region():
                    raise DuplicateScopeError(child, children[index])
                elif children[index].contains(child, Scope.source_region):
                    _insert(children[index], child)
                    return
                elif child.contains(children[index], Scope.source_region):
                    # Add the new child where children[index] was. Children[index] becomes a child
                    # of the newly added scope.
                    child.add_child(children[index])
                    children[index] = child

                    # The new scope may contain a range of children. We have to find all of these,
                    # add them as childrne of the new scope, and delete them from the current list
                    new_children = 1 # We've already added children[index]
                    pre = index - 1
                    while pre >= 0 and child.contains(children[pre], Scope.source_region):
                        # Since the old list is sorted, each previous child will be the first in the
                        # new list, so we add at index 0.
                        child.add_child(children[pre], 0)
                        children.pop(pre)
                        pre -= 1
                        new_children += 1

                    post = index + 1
                    while post < len(children) and child.contains(children[post], Scope.source_region):
                        # Since the old list is sorted, each post child will be the last in the
                        # new list, so we add at the end of that list.
                        child.add_child(children[post], len(child.children))
                        children.pop(post)
                        # No need to increment post, since pop will shift all of the indices by 1
                        new_children += 1

                    log.info('Inserted {new} in place of {old}, {num} scopes added as children of {new}',
                             new=child, old=children[index], num=new_children)
                    return

            root.add_child(child, index)
            log.info('Inserted {} as child of {}', child, root)

        child = Scope(region, name)
        log.debug('Inserting {} from top level.', child)
        _insert(self._root, child)
        self._size += 1
        self._needs_render = True

    def find(self, point):
        '''
        Return the smallest display region containing the given point, or None if no region contains
        the point.
        '''
        def _find(root, target):
            log.info('Looking for {} as a child of {}', target, root)

            if root is None or not root.contains(target, Scope.display_region):
                return None

            # Now we have to find it somewhere
            children, index = root.children, root.find_child(target, Scope.display_region)
            if index < len(children) and children[index].contains(target, Scope.display_region):
                return _find(children[index], target)

            # Couldn't find it in a child, so the root is as deep as we can go
            log.info('Successful find: {} is a child of {}', target, root)
            return root

        target = Point(point)
        log.debug('Searching for {} at top level.', target)
        child = _find(self._root, target)
        if not child or child == self._root:
            # We pretend the file-level scope doesn't exist
            return None
        return child.display_region()

    @test_only
    def set_top_level_scopes(self, *scopes):
        if scopes and type(scopes[0]) == type([]):
            scopes = scopes[0]

        self._root.children = []
        self._size = 0
        for scope in scopes:
            if not isinstance(scope, Scope):
                raise TypeError('Root of tree must be of type Scope')
            self._root.add_child(scope)

        # Normally, insert causes the parent tree to be set as each node is inserted. Since the
        # point of this function is to bypass that code path, we bite the bullet and do it manually.
        # Since we're going over the tree anyways, we add up the size as we go
        def _set_parent(root):
            root._parent = self
            for child in root.children:
                self._size += 1
                _set_parent(child)

        _set_parent(self._root)

        log.debug('set_top_level_scopes set tree to\n{}', self.render())

class Scope:
    '''
    A node in the scope tree. The node maps a region in the source file to a scope name (such as a
    class declaration or a function prototype). Each node keeps a list of children (nested scope)
    which is sorted in the same order as the scopes appear in the source. Each node knows about its
    region in the source code, and its region when displayed to the user in a scratch view.
    '''
    def __init__(self, region, name, parent=None):
        '''
        Create a new node with the given scope region. Offset is the position in the scratch view at
        which the node should start displaying itself and its children. Name should be the
        identifier of the scope, for example, a class declaration or a function signature.
        '''
        self.children = []
        self.name = name

        self._parent = parent
        self._region = region
        self._indent = 0

        # Display region bounds
        self._display_region = DisplayRegion(None, None, self.name)

    def __eq__(self, other):
        if not isinstance(other, Scope):
            return False

        # We don't need to compare display regions; if the name and source regions are the same,
        # so will be the display regions.
        return self.name == other.name and self.source_region() == other.source_region()

    def __repr__(self):
        # Give as much information as we can
        display_diag = '(unknown)'
        if self._parent and not self._parent._needs_render:
            display_diag = repr(self.display_region())

        # Render and append diagnostic information to the end of the line
        return re.sub(r'\n$', ' {{source={source}, display={display}}}\n'.format(
            source=repr(self.source_region()), display=display_diag), self.render())

    def add_child(self, child, index=None):
        '''
        Add the given scope as a child of this one.
        '''
        index = index or self.find_child(child, Scope.source_region)
        child._indent = self._indent + 1
        child._parent = self._parent

        self.validate_insert(index, child)
        self.children.insert(index, child)

    def find_child(self, child, region_func):
        if not self.children:
            # Insertion point into an empty list is always 0
            return 0

        start = 0
        end = len(self.children) - 1
        while start <= end:
            pivot = (start + end) // 2
            if child.left_of(self.children[pivot], region_func):
                end = pivot - 1
            elif self.children[pivot].left_of(child, region_func):
                start = pivot + 1
            else:
                # Either they're equal, pivot contains child, or vice versa. We don't care.
                return pivot

        # We couldn't find the child. Return the insertion point instead
        return start

    def source_region(self):
        '''
        Get the region in the source code represented by this node
        '''
        return self._region

    def display_region(self):
        '''
        Get the region in the scratch view that corresponds to this node
        '''
        if not self._parent:
            raise RenderError('Must set parent before calculating display region')
        if self._parent._needs_render:
            raise RenderError('Must render parent before caclulating display region')

        # If the preconditions are met, we should have a valid region
        assert self._display_region.begin() is not None and self._display_region.end() is not None

        return self._display_region

    def validate_insert(self, index, child):
        '''
        Do some error checking
        '''
        if self.intersects(child, Scope.source_region): raise ScopeIntersectError(self, child)
        if not self.contains(child, Scope.source_region): raise ScopeNestingError(self, child)
        assert index - 1 < 0 or index - 1 >= len(self.children) \
            or self.children[index - 1].left_of(child, Scope.source_region)
        assert index >= len(self.children) or child.left_of(self.children[index], Scope.source_region)

    def intersects(self, other, region_func):
        # It's useful to define intersection a bit differently than the Sublime API. We define it as
        # overlapping but not containing. Obviously, two valid scopes can never intersect, they can
        # only be nested or disjoint. So this is used only as an error condition.
        return region_func(self).intersects(region_func(other)) and \
            not (self.contains(other, region_func) or other.contains(self, region_func))

    def contains(self, other, region_func):
        if isinstance(other, Scope):
            return region_func(self).contains(region_func(other))
        elif isinstance(other, Point):
            return region_func(self).contains(other.offset)
        else:
            raise TypeError('other must be instance of Scope or Point')

    def left_of(self, other, region_func):
        if isinstance(other, Scope):
            if self.intersects(other, region_func):
                raise ScopeIntersectError(self, other)
            return region_func(self).end() < region_func(other).begin()
        elif isinstance(other, Point):
            return region_func(self).end() < other.offset
        else:
            raise TypeError('other must be instance of Scope or Point')

    # Set the bounds of the display region
    def display_start(self, offset):
        log.debug('{name}: begin display region at {offset}', name=self.name, offset=offset)
        self._display_region.set_begin(offset)
    def display_stop(self, offset):
        log.debug('{name}: end display region at {offset}', name=self.name, offset=offset)
        self._display_region.set_end(offset)

    def render(self):
        return ' '*self._indent*get_setting('indent_width') + self.name + '\n'

class FileScope(Scope):
    '''
    Special class to represent the top level scope in a file
    '''
    def __init__(self, view, parent):
        Scope.__init__(self, Region(0, view.size()), 'FILE', parent=parent)
        assert self._parent

    def __repr__(self):
        return ''

    def render(self):
        return ''

    def add_child(self, child, index=None):
        index = index or self.find_child(child, Scope.source_region)
        child._indent = 0
        child._parent = self._parent

        self.validate_insert(index, child)
        self.children.insert(index, child)

    def contains(self, *_):
        return True

    def display_start(self, offset):
        pass
    def display_stop(self, offset):
        pass

class Point:
    def __init__(self, offset):
        self.offset = offset

    def __repr__(self):
        return 'Point({})'.format(self.offset)

    def left_of(self, other, region_func):
        if isinstance(other, Scope):
            return self.offset < region_func(other).begin()
        elif isinstance(other, Point):
            return self.offset < other.offset
        else:
            raise TypeError('other must be instance of Point or Scope')
