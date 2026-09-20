import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    while True:
        try:
            n = int(next(it))
            c1 = int(next(it))
            c2 = int(next(it))
        except StopIteration:
            break
        if n == 0 and c1 == 0 and c2 == 0:
            break
        adj = [[] for _ in range(n + 1)]
        for _ in range(n - 1):
            u = int(next(it))
            v = int(next(it))
            adj[u].append(v)
            adj[v].append(u)
        dp0 = [0] * (n + 1)
        dp1 = [0] * (n + 1)
        def dfs(u, p):
            dp0[u] = 0
            dp1[u] = c1
            for v in adj[u]:
                if v == p:
                    continue
                dfs(v, u)
                dp0[u] += min(dp0[v], dp1[v])
                dp1[u] += dp0[v]
        dfs(1, 0)
        print(min(dp0[1], dp1[1]))

if __name__ == "__main__":
    solve()
