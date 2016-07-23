from sublime import load_settings

def get_setting(key, default=None):
    return load_settings("SublimeScopeTree.sublime-settings").get(key, default)
