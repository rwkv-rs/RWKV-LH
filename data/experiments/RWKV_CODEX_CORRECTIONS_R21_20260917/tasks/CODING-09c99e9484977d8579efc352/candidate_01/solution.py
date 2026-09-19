import sys
from array import array
n=int(sys.stdin.buffer.read());lp=array('i',[0])*(n+1)
for p in range(2,n+1):
 if lp[p]==0:
  for j in range(p,n+1,p):lp[j]=p
lo=n-lp[n]+1;ans=n
for x in range(lo,n+1):
 if lp[x]!=x:ans=min(ans,x-lp[x]+1)
print(ans)
