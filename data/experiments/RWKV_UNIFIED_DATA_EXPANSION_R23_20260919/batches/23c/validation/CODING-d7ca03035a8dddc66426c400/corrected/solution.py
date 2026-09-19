import sys

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            x, y, n = map(int, line.split())
            if x == 0 and y == 0 and n == 0:
                break
            result = pow(x, y, n)
            print(result)
        except ValueError:
            continue

if __name__ == "__main__":
    main()
