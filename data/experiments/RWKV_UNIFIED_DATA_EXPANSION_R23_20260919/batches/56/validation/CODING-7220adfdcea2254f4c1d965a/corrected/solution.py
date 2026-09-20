import sys
v=sys.stdin.buffer.read().split();H,W=map(int,v[:2]);g=v[2:];dp=[[10**9]*W for _ in range(H)];dp[0][0]=int(g[0][0]==35)
for r in range(H):
 for c in range(W):
  if r:dp[r][c]=min(dp[r][c],dp[r-1][c]+int(g[r][c]==35 and g[r-1][c]!=35))
  if c:dp[r][c]=min(dp[r][c],dp[r][c-1]+int(g[r][c]==35 and g[r][c-1]!=35))
print(dp[-1][-1])
