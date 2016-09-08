from sublime import active_window
import sublime_plugin

from SublimeScopeTree.lib.log import get_logger
from SublimeScopeTree.lib.parse import parse

log = get_logger('sublime_scope_tree')

class ScratchViewSetText(sublime_plugin.TextCommand):
    def run(self, edit, text):
        self.view.set_read_only(False)
        self.view.insert(edit, 0, text)
        self.view.set_read_only(True)
        log.debug('Set text in scratch view {}:\n{}', self.view.id(), text)

class ScopeTreeRender(sublime_plugin.TextCommand):
    def run(self, _):
        scratch_view = active_window().new_file()
        scratch_view.set_name(self.view.name() + ' -- ScopeTree')
        scratch_view.set_scratch(True)
        scratch_view.set_read_only(True)
        scratch_view.set_syntax_file(self.view.settings().get('syntax'))
        scratch_view.run_command('scratch_view_set_text', {'text': parse(self.view).render()})
