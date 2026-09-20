import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    N = int(next(it))
    M = int(next(it))
    s = int(next(it))
    t = int(next(it))
    d = [0] * (N + 1)
    for i in range(1, N + 1):
        d[i] = int(next(it))
    edges = []
    for _ in range(M):
        a = int(next(it))
        b = int(next(it))
        edges.append((a, b))

    INF = 10**18
    dp = [INF] * (N + 1)
    dp[s] = 0
    for _ in range(N):
        updated = False
        for a, b in edges:
            if dp[a] + d[b] < dp[b]:
                dp[b] = dp[a] + d[b]
                updated = True
        if not updated:
            break
    print(dp[t])

if __name__ == "__main__":
    main()
