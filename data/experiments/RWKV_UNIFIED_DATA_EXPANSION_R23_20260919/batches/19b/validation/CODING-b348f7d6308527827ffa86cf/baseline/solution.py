import sys

def solve():
    for line in sys.stdin:
        n = int(line.strip())
        if n == 0:
            break
        half = n // 2
        for a in range(10**half):
            for b in range(10**half):
                x = a * 10**half + b
                if (a + b) ** 2 == x:
                    print(x)

if __name__ == "__main__":
    solve()
