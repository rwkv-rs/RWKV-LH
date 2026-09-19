import sys


def solve() -> None:
    for line in sys.stdin:
        line = line.rstrip("\n")
        if line == "*":
            break
        if not line:
            continue
        n = len(line)
        if n == 0:
            print(-1)
            continue
        ok = True
        for i in range(n):
            if line[i] == "Y":
                if (i + 1) % 2 != 0:
                    ok = False
                    break
        if ok:
            print(2)
        else:
            print(-1)


if __name__ == "__main__":
    solve()
