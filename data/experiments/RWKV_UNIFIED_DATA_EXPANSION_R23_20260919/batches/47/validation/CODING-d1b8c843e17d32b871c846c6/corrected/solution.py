import sys
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));n,m,k=next(it),next(it),next(it);a=[next(it) for _ in range(n)];bonus=[[0]*n for _ in range(n)]
for _ in range(k):x,y,c=next(it)-1,next(it)-1,next(it);bonus[x][y]=c
N=1<<n;dp=array('q',[-1])*(N*n);index={1<<i:i for i in range(n)}
for i in range(n):dp[(1<<i)*n+i]=a[i]
answer=0
for mask in range(1,N):
 count=mask.bit_count()
 if count>m:continue
 base=mask*n;t=mask
 if count==m:
  while t:b=t&-t;answer=max(answer,dp[base+index[b]]);t^=b
  continue
 remaining=(N-1)^mask
 while t:
  b=t&-t;last=index[b];value=dp[base+last];t^=b
  if value<0:continue
  z=remaining
  while z:
   bit=z&-z;j=index[bit];pos=(mask|bit)*n+j;new=value+a[j]+bonus[last][j]
   if new>dp[pos]:dp[pos]=new
   z^=bit
print(answer)
