#!/usr/bin/env python3

import sys

MOD = 10007

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    T = int(next(it))
    out_lines = []
    for _ in range(T):
        n = int(next(it))
        c = int(next(it))
        m = [int(next(it)) for _ in range(n)]
        ans = 0
        for i in range(1, c):
            prod = 1
            for j in range(n):
                prod = (prod * m[j]) % MOD
            ans = (ans + prod) % MOD
        out_lines.append(str(ans))
    sys.stdout.write("\n".join(out_lines))

if __name__ == "__main__":
    solve()
