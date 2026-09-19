{
  "solution": "def count_pairs(n, m):\n    MOD = 10**9 + 7\n    dp = [[0] * (m + 1) for _ in range(n + 1)]\n    for i in range(1, n + 1):\n        dp[i][1] = i\n    for j in range(2, m + 1):\n        for i in range(1, n + 1):\n            dp[i][j] = dp[i][j - 1] + dp[i - 1][j - 1]\n            dp[i][j] %= MOD\n    return dp[n][m]\n\nif __name__ == '__main__':\n    n, m = map(int, input().split())\n    print(count_pairs(n, m))"
}
