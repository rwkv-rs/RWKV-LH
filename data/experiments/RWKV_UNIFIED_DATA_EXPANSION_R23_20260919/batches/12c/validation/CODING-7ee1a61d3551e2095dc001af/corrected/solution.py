import sys
from functools import lru_cache
it=iter(map(int,sys.stdin.buffer.read().split()));out=[];case=0
while True:
 try:n=next(it);m=next(it);k=next(it)
 except StopIteration:break
 case+=1;prefix=[[0]*(m+1) for _ in range(n+1)]
 for _ in range(k):x=next(it);y=next(it);prefix[x][y]+=1
 for i in range(1,n+1):
  for j in range(1,m+1):prefix[i][j]+=prefix[i-1][j]+prefix[i][j-1]-prefix[i-1][j-1]
 def cherries(top,bottom,left,right):return prefix[bottom][right]-prefix[top][right]-prefix[bottom][left]+prefix[top][left]
 @lru_cache(None)
 def solve(top,bottom,left,right):
  count=cherries(top,bottom,left,right)
  if count==1:return 0
  if count==0:return 10**9
  best=10**9
  for row in range(top+1,bottom):best=min(best,solve(top,row,left,right)+solve(row,bottom,left,right)+right-left)
  for col in range(left+1,right):best=min(best,solve(top,bottom,left,col)+solve(top,bottom,col,right)+bottom-top)
  return best
 out.append('Case '+str(case)+': '+str(solve(0,n,0,m)))
print('\n'.join(out))
