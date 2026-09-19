import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    N = int(next(it))
    K = int(next(it))
    X = [int(next(it)) for _ in range(N)]
    sign = [1 if x > 0 else -1 if x < 0 else 0 for x in X]
    prod = 1
    for s in sign:
        prod *= s
    prod_sign = 1 if prod > 0 else -1 if prod < 0 else 0
    out = []
    for _ in range(K):
        op = next(it)
        if op == 'C':
            i = int(next(it)) - 1
            v = int(next(it))
            old = X[i]
            X[i] = v
            old_s = sign[i]
            sign[i] = 1 if v > 0 else -1 if v < 0 else 0
            if old_s == 0:
                prod_sign = 0
            else:
                prod_sign *= sign[i]
        elif op == 'P':
            i = int(next(it)) - 1
            j = int(next(it)) - 1
            if sign[i] == 0 or sign[j] == 0:
                out.append('0')
            else:
                out.append('+' if prod_sign > 0 else '-')
    print(''.join(out))

if __name__ == '__main__':
    solve()
