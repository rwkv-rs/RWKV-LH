import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for m,n,t in zip(v,v,v):
 dp=[-1]*(t+1);dp[0]=0
 for x in range(1,t+1):
  if x>=m and dp[x-m]>=0:dp[x]=max(dp[x],dp[x-m]+1)
  if x>=n and dp[x-n]>=0:dp[x]=max(dp[x],dp[x-n]+1)
 used=t
 while dp[used]<0:used-=1
 out.append(str(dp[used])+((' '+str(t-used)) if used<t else ''))
print('\n'.join(out))
