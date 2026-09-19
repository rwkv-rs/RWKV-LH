import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    m = int(next(it))
    candies = []
    for _ in range(m):
        a = int(next(it))
        b = int(next(it))
        candies.append((a, b))

    def time_from(start):
        t = 0
        for a, b in candies:
            if a == start:
                t += 1
            else:
                t += (start - a) % n + 1
            t += (b - a) % n
        return t

    ans = [str(time_from(i + 1)) for i in range(n)]
    print(" ".join(ans))

if __name__ == "__main__":
    solve()
