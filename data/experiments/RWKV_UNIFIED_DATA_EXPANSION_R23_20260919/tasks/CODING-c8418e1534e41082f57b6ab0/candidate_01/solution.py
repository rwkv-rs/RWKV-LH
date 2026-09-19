import sys
v=iter(sys.stdin.read().split());out=[]
for _ in range(int(next(v))):
 n=int(next(v));grid=[next(v) for i in range(n)];vertices=[i*n+j for i in range(n) for j in range(n) if grid[i][j]=='X'];g={x:[] for x in vertices}
 for x in vertices:
  i,j=divmod(x,n)
  for a,b in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
   if 0<=a<n and 0<=b<n and a*n+b in g:g[x].append(a*n+b)
 found=set()
 def dfs(x,mask,depth):
  if depth==8:found.add(mask);return
  for y in g[x]:
   if not(mask>>y&1):dfs(y,mask|1<<y,depth+1)
 for x in vertices:dfs(x,1<<x,1)
 out.append(str(len(found)))
print('\n'.join(out))
