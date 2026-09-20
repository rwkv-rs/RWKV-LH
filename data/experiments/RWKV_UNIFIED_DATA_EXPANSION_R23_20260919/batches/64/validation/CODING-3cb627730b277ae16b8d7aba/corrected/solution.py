import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];ranges=list(zip(v[1::2],v[2::2]))[::-1];MOD=998244353;coordinates=sorted({x for l,r in ranges for x in (l,r+1)});inverses=[0]+[pow(i,MOD-2,MOD) for i in range(1,n+1)];dp=[1]+[0]*n
for left,right in zip(coordinates,coordinates[1:]):
 length=right-left;comb=[1]
 for t in range(1,n+1):comb.append(comb[-1]*(length+t-1)%MOD*inverses[t]%MOD)
 new=dp[:]
 for i in range(n):
  if not dp[i]:continue
  for j in range(i,n):
   l,r=ranges[j]
   if not(l<=left and right-1<=r):break
   new[j+1]=(new[j+1]+dp[i]*comb[j-i+1])%MOD
 dp=new
choices=1
for l,r in ranges:choices=choices*(r-l+1)%MOD
print(dp[n]*pow(choices,MOD-2,MOD)%MOD)
