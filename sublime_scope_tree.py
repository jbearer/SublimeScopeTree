import sublime_plugin

from SublimeScopeTree.lib.log import get_logger

log = get_logger('sublime_scope_tree')

class ScratchViewSetText(sublime_plugin.TextCommand):
    def run(self, edit, text):
        self.view.set_read_only(False)
        self.view.insert(edit, 0, text)
        self.view.set_read_only(True)
        log.debug('Set text in scratch view {}:\n{}', self.view.id(), text)
