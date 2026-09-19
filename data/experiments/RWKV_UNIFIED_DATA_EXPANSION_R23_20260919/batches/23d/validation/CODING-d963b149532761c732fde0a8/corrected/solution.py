import sys
v=list(map(int,sys.stdin.read().split()));n,k=v[:2];mod=1000000007;dp=[0]*(k+1);dp[0]=1
for cap in v[2:2+n]:
 nd=[0]*(k+1);window=0
 for x in range(k+1):
  window+=dp[x]
  if x>cap:window-=dp[x-cap-1]
  window%=mod;nd[x]=window
 dp=nd
print(dp[k])
