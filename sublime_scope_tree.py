from sublime import active_window
import sublime_plugin

from SublimeScopeTree.lib.log import get_logger
from SublimeScopeTree.lib.parse import parse

log = get_logger('sublime_scope_tree')

scope_trees = {}

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

        scope_trees[scratch_view.id()] = parse(self.view)

        scratch_view.run_command('scratch_view_set_text', {'text': scope_trees[scratch_view.id()].render()})

class ScopeTreeFold(sublime_plugin.TextCommand):
    def run(self, _):
        log.info('Click event in view {} at point {}', self.view.id(), self.view.sel()[0])

        tree = scope_trees[self.view.id()]
        region = tree.find(self.view.sel()[0].begin())

        if not region:
            log.info('Could not find region at point {}', self.view.sel()[0])
            return

        region.toggle_fold(self.view)

    def is_enabled(self):
        if self.view.id() not in scope_trees:
            log.debug('Rejected click event in view {}, {}', self.view.id(), scope_trees.keys())
            return False
        return True
