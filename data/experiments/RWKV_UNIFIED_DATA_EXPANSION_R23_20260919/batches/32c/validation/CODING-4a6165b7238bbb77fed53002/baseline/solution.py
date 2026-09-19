import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    W = int(next(it))
    B = int(next(it))
    X = int(next(it))
    c = [int(next(it)) for _ in range(n)]
    cost = [int(next(it)) for _ in range(n)]

    # dp[i][j] = minimal mana needed to reach tree i with j birds summoned
    # We use a list of dictionaries for each tree.
    dp = [{} for _ in range(n)]
    dp[0][0] = 0

    for i in range(n):
        for j, mana in dp[i].items():
            # Try summoning k birds from tree i
            for k in range(c[i] + 1):
                cost_k = k * cost[i]
                if mana + cost_k > W:
                    continue
                new_mana = mana + cost_k
                new_j = j + k
                # Move to next tree: restore X mana, capped at current capacity
                next_mana = min(new_mana + X, new_j * B)
                if next_mana > W:
                    next_mana = W
                if i + 1 < n:
                    if next_mana not in dp[i + 1] or dp[i + 1][next_mana] > new_j:
                        dp[i + 1][next_mana] = new_j
                else:
                    if new_j > dp[i + 1].get(next_mana, -1):
                        dp[i + 1][next_mana] = new_j

    # Find the maximum birds across all states at the last tree
    ans = 0
    for mana, birds in dp[n - 1].items():
        if birds > ans:
            ans = birds
    print(ans)

if __name__ == "__main__":
    main()
