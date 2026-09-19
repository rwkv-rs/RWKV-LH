import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    n, m = map(int, data[:2])
    ops = data[2:]

    arr = list(range(1, n + 1))
    reversed_flag = False
    swap_stack = []

    for i in range(m):
        op = ops[i]
        if op == '1':
            reversed_flag = not reversed_flag
        elif op == '2':
            reversed_flag = not reversed_flag
        elif op == '3':
            x = int(ops[i + 1])
            y = int(ops[i + 2])
            i += 2
            if reversed_flag:
                x = n - x + 1
                y = n - y + 1
            arr[x - 1], arr[y - 1] = arr[y - 1], arr[x - 1]
            swap_stack.append((x, y))
        elif op == '4':
            reversed_flag = not reversed_flag

    if reversed_flag:
        arr = arr[::-1]

    for x, y in reversed(swap_stack):
        if reversed_flag:
            x = n - x + 1
            y = n - y + 1
        arr[x - 1], arr[y - 1] = arr[y - 1], arr[x - 1]

    print(' '.join(map(str, arr)))

if __name__ == '__main__':
    main()
