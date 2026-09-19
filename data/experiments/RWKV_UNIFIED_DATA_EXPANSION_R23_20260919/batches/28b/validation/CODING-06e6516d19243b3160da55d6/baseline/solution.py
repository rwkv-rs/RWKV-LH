import sys

def is_palindrome(s: str) -> bool:
    return s == s[::-1]

def solve() -> None:
    for line in sys.stdin:
        word = line.rstrip('\n')
        n = len(word)
        if n < 6:
            continue

        found = False
        for i in range(n - 2):
            for j in range(i + 3, n - 1):
                a = word[i:j]
                b = word[j:j + 3]
                if len(a) < 3 or len(b) < 3:
                    continue
                if a == b or a in b or b in a:
                    continue
                if is_palindrome(a) and is_palindrome(b):
                    print(word)
                    found = True
                    break
            if found:
                break

if __name__ == '__main__':
    solve()
