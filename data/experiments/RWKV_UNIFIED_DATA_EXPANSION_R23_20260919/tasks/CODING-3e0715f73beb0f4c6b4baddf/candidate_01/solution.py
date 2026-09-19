import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);dp=[1];mod=1000000007
for kind in v[1:n]:
 if kind==b'f':dp=[0]+dp
 else:
  total=0
  for j in range(len(dp)-1,-1,-1):total=(total+dp[j])%mod;dp[j]=total
print(sum(dp)%mod)
