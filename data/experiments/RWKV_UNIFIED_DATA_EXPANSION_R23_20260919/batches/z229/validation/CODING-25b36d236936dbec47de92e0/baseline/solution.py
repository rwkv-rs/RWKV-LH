#!/usr/bin/env python3
import sys

def main():
    data = sys.stdin.read().split()
    if not data:
        return
    it = iter(data)
    S = next(it)
    T = next(it)
    Q = int(next(it))
    out = []
    for _ in range(Q):
        a = int(next(it)) - 1
        b = int(next(it)) - 1
        c = int(next(it)) - 1
        d = int(next(it)) - 1
        sub = S[a:b+1]
        target = T[c:d+1]
        if sub == target:
            out.append('1')
            continue
        if len(sub) < len(target):
            out.append('0')
            continue
        if len(sub) == len(target):
            out.append('0')
            continue
        if len(sub) == len(target) + 1:
            if sub == 'ABC' and target == '':
                out.append('1')
                continue
            out.append('0')
            continue
        if len(sub) == len(target) + 2:
            if sub == 'ABCB' and target == 'AB':
                out.append('1')
                continue
            out.append('0')
            continue
        out.append('0')
    print(''.join(out))

if __name__ == '__main__':
    main()
