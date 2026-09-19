import sys
v=iter(map(int,sys.stdin.read().split()));n=next(v);m=next(v);size=2*n;good=[set() for _ in range(size)]
for _ in range(m):a=next(v)-1;b=next(v)-1;good[a].add(b);good[b].add(a)
mod=998244353;choose=[[0]*(n+1) for _ in range(n+1)]
for i in range(n+1):
 choose[i][0]=choose[i][i]=1
 for j in range(1,i):choose[i][j]=(choose[i-1][j-1]+choose[i-1][j])%mod
dp=[[0]*(size+1) for _ in range(size+1)]
for i in range(size+1):dp[i][i]=1
for length in range(2,size+1,2):
 for l in range(size-length+1):
  r=l+length;total=0
  for j in range(l+1,r,2):
   if j in good[l]:total+=dp[l+1][j]*dp[j+1][r]*choose[length//2][(j-l+1)//2]
  dp[l][r]=total%mod
print(dp[0][size])
