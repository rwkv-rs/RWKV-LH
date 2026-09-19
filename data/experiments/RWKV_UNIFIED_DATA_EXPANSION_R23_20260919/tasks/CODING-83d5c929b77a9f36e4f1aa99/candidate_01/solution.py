import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n=next(it);a=[next(it) for _ in range(n)];out.append('YES' if all(x%2==a[0]%2 for x in a) else 'NO')
print('\n'.join(out))
