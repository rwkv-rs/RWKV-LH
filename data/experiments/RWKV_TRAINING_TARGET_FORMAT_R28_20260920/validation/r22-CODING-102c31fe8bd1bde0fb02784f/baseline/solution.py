import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    n = int(data[0])
    k = int(data[1])
    p = list(map(int, data[2:2+n]))
    
    def group_key(x):
        return (x // k) * k
    
    result = [group_key(x) for x in p]
    print(' '.join(map(str, result)))

if __name__ == '__main__':
    main()
