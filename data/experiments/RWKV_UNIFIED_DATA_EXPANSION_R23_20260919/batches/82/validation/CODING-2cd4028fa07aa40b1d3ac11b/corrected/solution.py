import sys,math
from array import array
v=sys.stdin.buffer.read().split();p=0;out=[];case=0
while p<len(v):
 n=int(v[p]);p+=1
 if not n:break
 points=[];length=0.0
 for _ in range(n):
  x,y,u,w=map(float,v[p:p+4]);p+=4;points.extend(((x,y),(u,w)));length+=math.hypot(x-u,y-w)
 width=2*n;size=1<<n;full=size-1
 distances=[[math.hypot(x-u,y-w) for u,w in points] for x,y in points]
 dp=array('d',[float('inf')])*(size*width)
 for i in range(n):dp[(1<<i)*width+2*i]=dp[(1<<i)*width+2*i+1]=0.0
 for mask in range(1,size):
  remaining=full^mask
  if not remaining:continue
  offset=mask*width;present=mask
  while present:
   bit=present&-present;present-=bit;j=bit.bit_length()-1
   for endpoint in (2*j,2*j+1):
    cost=dp[offset+endpoint];d=distances[endpoint];left=remaining
    while left:
     bit=left&-left;left-=bit;k=bit.bit_length()-1;target=(mask|bit)*width+2*k
     value=cost+d[2*k+1]
     if value<dp[target]:dp[target]=value
     value=cost+d[2*k]
     if value<dp[target+1]:dp[target+1]=value
 case+=1;answer=length+min(dp[full*width:]);out.append(f'Case {case}: {answer:.5f}')
print('\n'.join(out))
