import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    n, l, r = map(int, data[:3])
    w = list(map(int, data[3:3+n]))

    dp = [0] * (r + 1)
    dp[0] = 1

    for val in w:
        for s in range(r, val - 1, -1):
            dp[s] += dp[s - val]

    ans = sum(dp[l:r+1])
    print(ans)

if __name__ == "__main__":
    main()
