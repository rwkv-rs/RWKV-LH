#!/usr/bin/env python3
import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    m = int(next(it))
    T = int(next(it))
    M = [[int(next(it)) for _ in range(m)] for _ in range(n)]

    # prefix sums for rows and columns
    row_pref = [[0] * (m + 1) for _ in range(n)]
    col_pref = [[0] * (m + 1) for _ in range(n)]
    for i in range(n):
        for j in range(m):
            row_pref[i][j + 1] = row_pref[i][j] + M[i][j]
            col_pref[i][j + 1] = col_pref[i][j] + M[j][i]

    def square_sum(x, y, k):
        # sum of k x k square with top-left (x, y)
        return (
            row_pref[x + k - 1][y + k] - row_pref[x + k - 1][y]
            + col_pref[y + k - 1][x + k] - col_pref[y + k - 1][x]
        )

    out_lines = []
    for _ in range(T):
        x = int(next(it)) - 1
        y = int(next(it)) - 1
        k = int(next(it))
        s = square_sum(x, y, k)
        out_lines.append('Y' if s == 0 else 'N')

    sys.stdout.write('\n'.join(out_lines))

if __name__ == '__main__':
    solve()
