import sys

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            continue
        k_str, x_str, y_str = parts
        try:
            k = int(k_str)
            x = int(x_str)
            y = int(y_str)
        except ValueError:
            continue
        if k == 0 and x == 0 and y == 0:
            break
        if k < 1 or k > 512:
            continue
        count = 0
        for i in range(k, 0, -1):
            if x >= i and y >= i:
                count += 1
        print(f"{count:3d}")

if __name__ == "__main__":
    main()
