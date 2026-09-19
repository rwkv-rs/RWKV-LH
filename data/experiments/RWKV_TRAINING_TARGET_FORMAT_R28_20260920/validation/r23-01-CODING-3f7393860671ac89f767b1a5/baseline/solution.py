import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    b = [int(next(it)) for _ in range(n)]
    a = [int(next(it)) for _ in range(n)]
    for i in range(1, n):
        x = int(next(it)) - 1
        k = int(next(it))
        if b[i] < a[i]:
            need = a[i] - b[i]
            if b[x] >= need * k:
                b[x] -= need * k
            else:
                print("NO")
                return
    print("YES")

if __name__ == "__main__":
    solve()
