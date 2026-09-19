import sys

def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    limit = int(n ** 0.5) + 1
    for i in range(3, limit, 2):
        if n % i == 0:
            return False
    return True

def main():
    data = sys.stdin.read().strip()
    if not data:
        print(0)
        return
    try:
        n = int(data)
    except ValueError:
        print(0)
        return
    if n < 2:
        print(0)
        return
    count = 0
    for i in range(2, n + 1):
        if is_prime(i):
            count += 1
    print(count)

if __name__ == "__main__":
    main()
