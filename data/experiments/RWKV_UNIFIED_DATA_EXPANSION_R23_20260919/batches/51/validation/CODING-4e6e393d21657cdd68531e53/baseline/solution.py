import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    t = int(next(it))
    out = []
    for _ in range(t):
        n = int(next(it))
        K = int(next(it))
        D = int(next(it))
        X = [int(next(it)) for _ in range(n)]
        L = [int(next(it)) for _ in range(n)]
        # dp[i][0] = max distance from start to obstacle i when lane at i is 1
        # dp[i][1] = max distance from start to obstacle i when lane at i is 2
        dp = [[0, 0] for _ in range(n)]
        for i in range(n):
            if i == 0:
                dp[i][0] = X[i]
                dp[i][1] = X[i]
            else:
                # from previous obstacle j < i, switch at X[j], then drive to X[i]
                best = 0
                for j in range(i):
                    if L[j] != L[i]:
                        dist = X[i] - X[j]
                        if dist >= D:
                            cand = dp[j][1 - L[i]] + dist
                            if cand > best:
                                best = cand
                dp[i][L[i] - 1] = best
        ans = max(dp[n - 1])
        if ans >= K:
            out.append(str(K))
        else:
            out.append(str(ans))
    sys.stdout.write("\n".join(out))

if __name__ == "__main__":
    solve()
