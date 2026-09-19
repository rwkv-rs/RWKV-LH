import sys,itertools
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);a=[next(v) for i in range(n)];groups=[x for x,g in itertools.groupby(a)];out.append('yes' if a==a[::-1] and groups==list(range(1,8))+list(range(6,0,-1)) else 'no')
print('\n'.join(out))
