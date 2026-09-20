import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    N = int(next(it))
    points = []
    for _ in range(N):
        x = int(next(it))
        y = int(next(it))
        points.append((x, y))

    # Count collinear triples
    collinear_triples = 0
    for i in range(N):
        for j in range(i + 1, N):
            xi, yi = points[i]
            xj, yj = points[j]
            dx = xj - xi
            dy = yj - yi
            if dx == 0 and dy == 0:
                continue
            slope = (dy, dx)
            cnt = 1
            for k in range(j + 1, N):
                xk = points[k][0]
                yk = points[k][1]
                if dx * (yk - yi) == dy * (xk - xi):
                    cnt += 1
            collinear_triples += cnt * (cnt - 1) // 2

    total = N * (N - 1) * (N - 2) * (N - 3) // 24
    ans = total - collinear_triples
    print(ans)

if __name__ == "__main__":
    solve()
