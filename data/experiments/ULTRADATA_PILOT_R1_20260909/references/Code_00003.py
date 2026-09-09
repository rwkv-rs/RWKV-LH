"""Independent validator reference: rectangle dynamic programming, not Agent data."""
from functools import cache
import sys


def solve(width, height, points):
    @cache
    def collect(left, right, bottom, top):
        best = 0
        for x, y in points:
            if left <= x <= right and bottom <= y <= top:
                value = right - left + top - bottom + 1
                value += collect(left, x - 1, bottom, y - 1)
                value += collect(left, x - 1, y + 1, top)
                value += collect(x + 1, right, bottom, y - 1)
                value += collect(x + 1, right, y + 1, top)
                best = max(best, value)
        return best
    return collect(1, width, 1, height)


if __name__ == '__main__':
    values = list(map(int, sys.stdin.buffer.read().split()))
    width, height, count = values[:3]
    points = list(zip(values[3::2], values[4::2]))
    assert count == len(points)
    print(solve(width, height, points))
