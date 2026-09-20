import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    m, n = map(int, data[:2])
    grid = [list(map(int, data[i*m:(i+1)*m])) for i in range(n)]

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = grid[i-1][j-1] + max(dp[i-1][j-1], dp[i-1][j])

    print(dp[n][1])
    print(dp[n][m])
    print(dp[n][m] - dp[n][1])

if __name__ == "__main__":
    main()
