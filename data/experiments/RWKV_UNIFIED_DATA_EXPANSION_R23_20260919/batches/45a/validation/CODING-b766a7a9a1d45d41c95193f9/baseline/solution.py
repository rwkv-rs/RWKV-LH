import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    n = int(data[0])
    H = []
    idx = 1
    for i in range(n):
        row = list(map(int, data[idx:idx+n]))
        H.append(row)
        idx += n

    # DP over subsets of girls
    # dp[mask] = (max_sum, list_of_boys_used)
    dp = [(-1, []) for _ in range(1 << n)]
    dp[0] = (0, [])

    for mask in range(1 << n):
        if dp[mask][0] == -1:
            continue
        boys_used = dp[mask][1]
        for i in range(n):
            if mask & (1 << i):
                continue
            new_mask = mask | (1 << i)
            new_sum = dp[mask][0] + H[boys_used[-1]][i]
            new_boys = boys_used + [i]
            if new_sum > dp[new_mask][0]:
                dp[new_mask] = (new_sum, new_boys)

    max_sum = dp[(1 << n) - 1][0]
    boys_used = dp[(1 << n) - 1][1]

    # Build intersection
    intersection = []
    for i in range(n):
        if boys_used[i] == i:
            intersection.append((i + 1, i + 1))

    print(max_sum)
    for i, j in intersection:
        print(i, j)

if __name__ == "__main__":
    main()
