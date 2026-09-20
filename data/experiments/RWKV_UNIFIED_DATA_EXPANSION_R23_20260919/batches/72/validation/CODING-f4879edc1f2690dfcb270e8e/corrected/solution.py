import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m,step=v[:3];a=v[3:];MOD=1000000007;dp=[1]+[0]*n;step%=MOD;limit=min(n,m)
for j,x in enumerate(a,1):
 factor=j*step%MOD
 for r in range(min(j,limit),0,-1):dp[r]=((x+r*step)*dp[r]+factor*dp[r-1])%MOD
 dp[0]=dp[0]*x%MOD
answer=dp[0];weight=1;inverse=pow(n,MOD-2,MOD)
for r in range(1,limit+1):weight=weight*(m-r+1)%MOD*inverse%MOD;answer=(answer+weight*dp[r])%MOD
print(answer)
