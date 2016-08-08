import os
import json
from nose.tools import nottest

from lib.test import test_only

# Mock sublime api, since we can't import sublime_api outside of sublime

class View:
    @test_only
    def __init__(self, size):
        self._size = size

    def size(self):
        return self._size

@test_only
@nottest
def test_view():
    return View(10000)

class Region:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __lt__(self, other):
        return self.begin() < other.begin()

    def begin(self):
        return min(self.a, self.b)

    def end(self):
        return max(self.a, self.b)

    def contains(self, other):
        if isinstance(other, Region):
            return self.contains(other.begin()) and self.contains(other.end())
        else:
            # Point
            return self.begin() <= other and other <= self.end()

    def intersects(self, other):
        return self.contains(other.begin()) or self.contains(other.end()) or \
            other.contains(self.begin()) or other.contains(self.end())

    def size(self):
        return self.end() - self.begin()

    def __eq__(self, other):
        return self.begin() == other.begin() and self.end() == other.end()

    def __repr__(self):
        return '({begin}, {end})'.format(begin=self.begin(), end=self.end())

    @test_only
    def center(self):
        return (self.end() + self.begin()) / 2

class Settings:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

def load_settings(base_name, cache={}):
    assert base_name == 'SublimeScopeTree.sublime-settings'

    if base_name not in cache:
        path = os.path.dirname(__file__) + '/../SublimeScopeTree.sublime-settings'
        with open(path, 'r') as settings:
            cache[base_name] = Settings(json.loads(settings.read()))
    return cache[base_name]

@test_only
def inject_settings(**kwargs):
    '''
    Convenience method for dynamically playing around with settings
    '''
    s = load_settings('SublimeScopeTree.sublime-settings')
    for key, value in kwargs.items():
        s.set(key, value)
