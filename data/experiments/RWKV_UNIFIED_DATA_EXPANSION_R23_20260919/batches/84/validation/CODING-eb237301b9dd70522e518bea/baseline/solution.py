import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    N = int(next(it))
    M = int(next(it))
    close_times = [int(next(it)) for _ in range(N)]
    gems = []
    for _ in range(M):
        r = int(next(it))
        v = int(next(it))
        t = int(next(it))
        gems.append((r, v, t))

    INF = -10**18
    dp = [INF] * N
    dp[0] = 0

    for r, v, t in gems:
        for i in range(N):
            if dp[i] == INF:
                continue
            if i + 1 < N and dp[i] + t <= close_times[i + 1]:
                dp[i + 1] = max(dp[i + 1], dp[i] + v)

    print(max(dp))

if __name__ == "__main__":
    main()
