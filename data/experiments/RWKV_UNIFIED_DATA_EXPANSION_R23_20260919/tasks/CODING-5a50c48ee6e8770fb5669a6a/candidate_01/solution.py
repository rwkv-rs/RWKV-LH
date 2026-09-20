import sys,math
v=list(map(int,sys.stdin.buffer.read().split()))
print('\n'.join(str(math.gcd(n-1,m-1)+1) for n,m in zip(v[::2],v[1::2])))
