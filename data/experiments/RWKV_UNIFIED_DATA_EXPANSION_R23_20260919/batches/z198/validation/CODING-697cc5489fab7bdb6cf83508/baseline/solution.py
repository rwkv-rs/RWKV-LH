import sys

def main():
    input = sys.stdin.readline
    N = int(input())
    lamps = [tuple(map(int, input().split())) for _ in range(N)]
    lamps.sort()
    X = lamps[0][0]
    for x, y in lamps:
        if x != X:
            print(X)
            return
    print(X)

if __name__ == "__main__":
    main()
