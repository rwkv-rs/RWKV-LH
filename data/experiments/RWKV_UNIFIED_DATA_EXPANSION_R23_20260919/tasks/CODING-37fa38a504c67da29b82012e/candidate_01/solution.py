import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);q=next(it);a=[[next(it) for _ in range(m)] for _ in range(n)];p=[[0]*m for _ in range(n)]
for i in range(1,n):
 running=0
 for j in range(1,m):
  running+=a[i][j]+a[i-1][j-1]!=a[i-1][j]+a[i][j-1];p[i][j]=p[i-1][j]+running
out=[]
for _ in range(q):
 x=next(it)-1;y=next(it)-1;k=next(it);r=x+k-1;c=y+k-1;bad=p[r][c]-p[x][c]-p[r][y]+p[x][y];out.append('N' if bad else 'Y')
print('\n'.join(out))
