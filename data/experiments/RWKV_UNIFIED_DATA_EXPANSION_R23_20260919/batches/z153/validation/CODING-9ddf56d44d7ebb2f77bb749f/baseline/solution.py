import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    t = int(next(it))
    n = int(next(it))
    d = int(next(it))
    a = [int(next(it)) for _ in range(t)]
    queries = []
    for _ in range(n):
        x = int(next(it))
        y = int(next(it))
        queries.append((x, y))

    # Precompute prefix sums of a_i
    prefix = [0] * (t + 1)
    for i in range(t):
        prefix[i + 1] = prefix[i] + a[i]

    # Precompute factorials and inverse factorials up to max needed
    max_fact = max(prefix[t], max(x for x, _ in queries)) + d
    fact = [1] * (max_fact + 1)
    inv_fact = [1] * (max_fact + 1)
    for i in range(1, max_fact + 1):
        fact[i] = fact[i - 1] * i % MOD
    inv_fact[max_fact] = pow(fact[max_fact], MOD - 2, MOD)
    for i in range(max_fact, 0, -1):
        inv_fact[i - 1] = inv_fact[i] * i % MOD

    def comb(n, k):
        if k < 0 or k > n:
            return 0
        return fact[n] * inv_fact[k] % MOD * inv_fact[n - k] % MOD

    def prob_color(x, y):
        # Probability that the x-th draw is color y
        # P(c_x = y) = (a_y + (x-1)*d) / (prefix[t] + (x-1)*d)
        numerator = a[y - 1] + (x - 1) * d
        denominator = prefix[t] + (x - 1) * d
        return numerator * pow(denominator, MOD - 2, MOD) % MOD

    # Compute the probability of the sequence
    prob = 1
    for x, y in queries:
        prob = prob * prob_color(x, y) % MOD

    # Output as fraction numerator/denominator
    # Since each step is independent, the probability is a product of fractions
    # We need to output as a single fraction in simplest form
    # We can compute the numerator and denominator separately
    numerator = 1
    denominator = 1
    for x, y in queries:
        numerator = numerator * (a[y - 1] + (x - 1) * d) % MOD
        denominator = denominator * (prefix[t] + (x - 1) * d) % MOD
    # Reduce the fraction
    g = math.gcd(numerator, denominator)
    numerator //= g
    denominator //= g
    print(f"{numerator}/{denominator}")

if __name__ == "__main__":
    solve()
