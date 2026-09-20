import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    N = int(data[0])
    X = int(data[1])
    A = list(map(int, data[2:2+N]))

    # dp[s] = minimal number of items to achieve sum s
    dp = [float('inf')] * (X + 1)
    dp[0] = 0

    for a in A:
        for s in range(X, a - 1, -1):
            if dp[s - a] + 1 < dp[s]:
                dp[s] = dp[s - a] + 1

    k = dp[X]
    print(k)

if __name__ == "__main__":
    main()
