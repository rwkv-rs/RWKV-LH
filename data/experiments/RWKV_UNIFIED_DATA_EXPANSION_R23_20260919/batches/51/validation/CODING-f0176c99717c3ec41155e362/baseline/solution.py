import sys


def parse_expr(s, i):
    if i >= len(s):
        return None, i
    if s[i] == '(':
        i += 1
        val, i = parse_expr(s, i)
        if i >= len(s) or s[i] != ')':
            return None, i
        i += 1
        return val, i
    if s[i] == '0' or s[i] == '1':
        j = i
        while j < len(s) and s[j] in '01':
            j += 1
        num = int(s[i:j], 2)
        return num, j
    return None, i


def parse_term(s, i):
    val, i = parse_expr(s, i)
    if val is None:
        return None, i
    while i < len(s) and s[i] == '*':
        i += 1
        val2, i = parse_expr(s, i)
        if val2 is None:
            return None, i
        val = val * val2
    return val, i


def parse_expr_top(s, i):
    val, i = parse_term(s, i)
    if val is None:
        return None, i
    while i < len(s) and s[i] == '+':
        i += 1
        val2, i = parse_term(s, i)
        if val2 is None:
            return None, i
        val = val + val2
    return val, i


def solve(s):
    n = len(s)
    best = None
    for mask in range(1 << n):
        t = list(s)
        ok = True
        for i in range(n):
            if t[i] == '.':
                if (mask >> i) & 1:
                    t[i] = '1'
                else:
                    t[i] = '0'
        try:
            val, pos = parse_expr_top(t, 0)
            if pos == n and val is not None:
                if best is None or val > best:
                    best = val
        except:
            pass
    return best


def main():
    s = sys.stdin.readline().rstrip('\n')
    ans = solve(s)
    print(ans if ans is not None else -1)


if __name__ == '__main__':
    main()
