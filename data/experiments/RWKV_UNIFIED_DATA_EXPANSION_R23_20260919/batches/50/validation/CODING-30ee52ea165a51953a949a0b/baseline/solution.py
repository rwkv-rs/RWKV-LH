import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    N = int(next(it))
    K = int(next(it))
    S = int(next(it))
    ranks = [int(next(it)) for _ in range(K)]
    cows = [int(next(it)) for _ in range(N)]

    def rank_of(x):
        return ranks.index(x) + 1

    def compare(a, b):
        ra = rank_of(a)
        rb = rank_of(b)
        if ra != rb:
            return ra - rb
        return a - b

    def is_match(start):
        for i in range(K):
            if compare(cows[start + i], cows[start + i + 1]) != 1:
                return False
        return True

    count = 0
    for start in range(N - K + 1):
        if is_match(start):
            count += 1

    print(count)
    for start in range(N - K + 1):
        if is_match(start):
            print(start + 1)

if __name__ == "__main__":
    main()
