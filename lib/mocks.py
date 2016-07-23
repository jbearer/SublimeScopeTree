from lib.test import test_only

# Mock sublime api, since we can't import sublime_api outside of sublime

class Region:
    def __init__(self, a, b):
        self.a = a
        self.b = b

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

    # Implement more functions as needed

    @test_only
    def center(self):
        return (self.end() + self.begin()) / 2
