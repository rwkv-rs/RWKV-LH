import sys
sys.setrecursionlimit(10000)
v=iter(map(int,sys.stdin.read().split()));n=next(v);k=next(v);weights=[next(v) for i in range(n)];g=[[] for i in range(n)]
for _ in range(n-1):
 a=next(v)-1;b=next(v)-1;g[a].append(b);g[b].append(a)
cap=k+1;bad=-10**30
def dfs(a,parent):
 dp=[bad]*(cap+1);dp[0]=weights[a];dp[cap]=0
 for b in g[a]:
  if b==parent:continue
  child=dfs(b,a);shifted=[bad]*(cap+1)
  for distance,value in enumerate(child):shifted[min(cap,distance+1)]=max(shifted[min(cap,distance+1)],value)
  merged=[bad]*(cap+1)
  for x,vx in enumerate(dp):
   if vx==bad:continue
   for y,vy in enumerate(shifted):
    if vy!=bad and x+y>k:merged[min(x,y)]=max(merged[min(x,y)],vx+vy)
  dp=merged
 return dp
print(max(dfs(0,-1)))
