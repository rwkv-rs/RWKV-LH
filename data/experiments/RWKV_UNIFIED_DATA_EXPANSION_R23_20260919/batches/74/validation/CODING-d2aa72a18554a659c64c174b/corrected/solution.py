import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];ranges=list(zip(v[2::2],v[3::2]));MOD=998244353;points=sorted({0}|{x for pair in ranges for x in pair});inverse=[0]+[pow(i,MOD-2,MOD) for i in range(1,n+2)];denominators=[pow(r-l,MOD-2,MOD) for l,r in ranges];answer=0
for left,right in zip(points,points[1:]):
 sure=sum(l>=right for l,r in ranges);active=[(r-left,inv) for (l,r),inv in zip(ranges,denominators) if l<=left<r];need=k-sure;width=right-left
 if need<=0:answer+=width;continue
 if need>len(active):continue
 dp=[[1]]
 for numerator,inv in active:
  q=numerator*inv%MOD;b=(-inv)%MOD;new=[[0]*(len(dp[0])+1) for _ in range(len(dp)+1)]
  for count,poly in enumerate(dp):
   for degree,value in enumerate(poly):
    new[count][degree]=(new[count][degree]+value*(1-q))%MOD;new[count][degree+1]=(new[count][degree+1]-value*b)%MOD
    new[count+1][degree]=(new[count+1][degree]+value*q)%MOD;new[count+1][degree+1]=(new[count+1][degree+1]+value*b)%MOD
  dp=new
 polynomial=[sum(poly[j] for poly in dp[need:])%MOD for j in range(len(dp[0]))];power=width
 for j,coefficient in enumerate(polynomial):answer=(answer+coefficient*power*inverse[j+1])%MOD;power=power*width%MOD
print(answer%MOD)
