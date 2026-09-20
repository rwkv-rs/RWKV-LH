import sys,bisect,functools
v=list(map(int,sys.stdin.buffer.read().split()));queries=v[1:];M=max(queries);MOD=1000000001;smooth=[];a=1
while a<=M:
 b=a
 while b<=M:smooth.append(b);b*=3
 a*=2
smooth.sort()
@functools.lru_cache(None)
def component(bound):
 widths=[];a=1
 while a<=bound:
  width=0;b=a
  while b<=bound:width+=1;b*=3
  widths.append(width);a*=2
 dp=[1];oldwidth=0
 for width in widths:
  if width>oldwidth:dp+= [0]*((1<<width)-len(dp));oldwidth=width
  sums=dp[:]
  for bit in range(oldwidth):
   step=1<<bit
   for base in range(0,len(sums),2*step):
    for j in range(base+step,base+2*step):sums[j]=(sums[j]+sums[j-step])%MOD
  maskall=len(sums)-1;dp=[sums[maskall^mask] if not(mask&(mask<<1)) else 0 for mask in range(1<<width)];oldwidth=width
 return sum(dp)%MOD
def coprime6(x):return x-x//2-x//3+x//6
out=[]
for n in queries:
 answer=1;l=1
 while l<=n:
  q=n//l;r=n//q;count=coprime6(r)-coprime6(l-1)
  if count:answer=answer*pow(component(smooth[bisect.bisect_right(smooth,q)-1]),count,MOD)%MOD
  l=r+1
 out.append(str(answer))
print('\n'.join(out))
