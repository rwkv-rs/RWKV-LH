import sys
v=sys.stdin.read().split();n,m=map(int,v[:2]);grid=v[2:];answer=0
for i in range(n):
 for j in range(m):
  if grid[i][j]=='*' and (i==0 or grid[i-1][j]!='*') and (j==0 or grid[i][j-1]!='*'):answer+=1
print(answer)
