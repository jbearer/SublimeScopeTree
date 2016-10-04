from sublime import Region

from SublimeScopeTree.lib.log import get_logger

log = get_logger('lib.display')

class DisplayRegion(Region):
    '''
    This class wraps Sublime's region type to keep track of whether a region is folded or not, and
    provides an API for folding and unfolding the region.
    '''
    def __init__(self, a, b, parent, folded=False):
        Region.__init__(self, a, b)
        self._parent = parent
        self._is_folded = folded

    def toggle_fold(self, view):
        view.sel().clear()

        # Begin selection after name so that the our name is still visible after folding.
        # Only our children will be hidden.
        view.sel().add(Region(self.begin() + len(self._parent.render()) - 1, self.end()))

        if self._is_folded:
            log.info('Unfolding region {} in view {}', self, view.id())
            command = 'unfold'
        else:
            log.info('Folding region {} in view {}', self, view.id())
            command = 'fold'

        view.run_command(command)
        view.sel().clear()
        self._is_folded = not self._is_folded

    def set_begin(self, offset):
        self.a = offset

    def set_end(self, offset):
        self.b = offset
