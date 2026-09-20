import sys

def solve():
    m, d = map(int, sys.stdin.readline().split())
    a_str = sys.stdin.readline().strip()
    b_str = sys.stdin.readline().strip()
    n = len(a_str)
    assert len(b_str) == n

    MOD = 10**9 + 7

    def count_up_to(x):
        if not x:
            return 0
        n = len(x)
        dp = [[[0] * 2 for _ in range(2)] for _ in range(n + 1)]
        dp[0][0][1] = 1
        for i in range(n):
            for tight in (0, 1):
                for mod in range(m):
                    cur = dp[i][tight][mod]
                    if cur == 0:
                        continue
                    lo = 0
                    hi = int(x[i]) if tight else 9
                    for digit in range(lo, hi + 1):
                        if digit != d:
                            continue
                        new_tight = tight and (digit == hi)
                        new_mod = (mod * 10 + digit) % m
                        dp[i + 1][new_tight][new_mod] += cur
                        if dp[i + 1][new_tight][new_mod] >= MOD:
                            dp[i + 1][new_tight][new_mod] -= MOD
        return sum(dp[n][0][mod] for mod in range(m)) % MOD

    ans = (count_up_to(b_str) - count_up_to(a_str[:-1])) % MOD
    print(ans)

if __name__ == "__main__":
    solve()
