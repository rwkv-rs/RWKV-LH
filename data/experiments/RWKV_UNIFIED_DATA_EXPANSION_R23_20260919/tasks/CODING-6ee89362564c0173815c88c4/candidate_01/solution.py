import sys
v=sys.stdin.read().split();s=v[1];mod=998244353;dp=[[0]*10 for _ in range(1024)]
for char in s:
 c=ord(char)-65;bit=1<<c
 for mask in range(1024):
  if mask&bit:
   prior=mask^bit;dp[mask][c]=(2*dp[mask][c]+(sum(dp[prior]) if prior else 1))%mod
print(sum(map(sum,dp))%mod)
