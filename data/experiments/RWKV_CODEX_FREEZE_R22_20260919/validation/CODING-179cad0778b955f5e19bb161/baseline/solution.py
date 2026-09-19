#!/usr/bin/env python3
import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    q = int(next(it))
    books = [int(next(it)) for _ in range(n)]
    books.sort()
    out = []
    for _ in range(q):
        l = int(next(it))
        d = int(next(it))
        target = int(d) * (10 ** l)
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if books[mid] < target:
                lo = mid + 1
            else:
                hi = mid
        if lo < n and books[lo] == target:
            out.append(str(books[lo]))
        else:
            out.append("-1")
    sys.stdout.write("\n".join(out))

if __name__ == "__main__":
    main()
