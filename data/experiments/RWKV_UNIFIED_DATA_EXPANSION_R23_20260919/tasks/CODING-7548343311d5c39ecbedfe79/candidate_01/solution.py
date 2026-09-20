import sys,math
r,g=map(int,sys.stdin.buffer.read().split());h=(math.isqrt(1+8*(r+g))-1)//2;total=h*(h+1)//2;r,g=min(r,g),max(r,g);MOD=1000000007;dp=[0]*(r+1);dp[0]=1;used=0
for level in range(1,h+1):
 used+=level
 for x in range(min(r,used),level-1,-1):
  value=dp[x]+dp[x-level];dp[x]=value-MOD if value>=MOD else value
print(sum(dp[max(0,total-g):])%MOD)
