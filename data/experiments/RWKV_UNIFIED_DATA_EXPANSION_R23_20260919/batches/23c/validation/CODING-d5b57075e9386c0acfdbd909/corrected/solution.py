import sys

def main():
    lines = []
    for line in sys.stdin:
        stripped = line.rstrip('\n')
        if stripped == '0':
            break
        lines.append(stripped)

    seen = set()
    non_shadow = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            non_shadow.append(line)

    print(''.join(non_shadow))

if __name__ == '__main__':
    main()
