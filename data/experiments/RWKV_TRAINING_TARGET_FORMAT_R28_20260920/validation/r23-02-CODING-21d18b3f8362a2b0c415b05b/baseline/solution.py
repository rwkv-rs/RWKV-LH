#!/usr/bin/env python3

import sys

MOD = 10**9 + 7

def solve() -> None:
    data = sys.stdin.read().strip().split()
    if not data:
        return
    n = int(data[0])
    a = list(map(int, data[1:1 + n]))

    freq = {}
    for x in a:
        freq[x] = freq.get(x, 0) + 1

    ans = 0
    for x, cnt in freq.items():
        if cnt >= 4:
            ans += cnt * (cnt - 1) * (cnt - 2) * (cnt - 3) // 24
        if cnt >= 2:
            for y, cnt2 in freq.items():
                if y <= x:
                    continue
                if y == x:
                    continue
                if cnt2 >= 2:
                    ans += cnt * (cnt - 1) // 2 * cnt2 * (cnt2 - 1) // 2
    print(ans % MOD)

if __name__ == "__main__":
    solve()
