import sys
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i in range(v[0]):
 n,k=v[1+2*i:3+2*i];out.append('POSSIBLE' if n>=3 and 2*n+1<=3**k else 'IMPOSSIBLE')
print('\n'.join(out))
