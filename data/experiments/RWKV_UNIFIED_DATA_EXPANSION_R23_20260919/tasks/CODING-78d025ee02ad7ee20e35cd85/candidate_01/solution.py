import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);commands=v[1:1+n];dp=[1];mod=1000000007
for previous in commands[:-1]:
 if previous==b'f':dp=[0]+dp
 else:
  total=0
  for i in range(len(dp)-1,-1,-1):total=(total+dp[i])%mod;dp[i]=total
print(sum(dp)%mod)
