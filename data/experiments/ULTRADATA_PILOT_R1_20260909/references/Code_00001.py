"""Independent validator reference: boundary inclusion-exclusion, not Agent data."""
import math
import sys


def solve(r, c, h, w, desks, racks):
    total = 0
    for mask in range(16):
        rows = ({0} if mask & 1 else set()) | ({h - 1} if mask & 2 else set())
        cols = ({0} if mask & 4 else set()) | ({w - 1} if mask & 8 else set())
        cells = (h - len(rows)) * (w - len(cols))
        ways = math.comb(cells, desks) * math.comb(cells - desks, racks) if cells >= desks + racks else 0
        total += (-1 if mask.bit_count() % 2 else 1) * ways
    return total * (r - h + 1) * (c - w + 1) % 1000000007


if __name__ == '__main__':
    print(solve(*map(int, sys.stdin.buffer.read().split())))
