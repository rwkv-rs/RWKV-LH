import sys
it=iter(sys.stdin.buffer.read().split());n,m,k=int(next(it)),int(next(it)),int(next(it));grid=[next(it) for _ in range(n)]
if n>m:grid=[bytes(grid[r][c] for r in range(n)) for c in range(m)];n,m=m,n
stars=[[int(grid[r][c]==49 and grid[r-1][c]==49 and grid[r+1][c]==49 and grid[r][c-1]==49 and grid[r][c+1]==49) for c in range(1,m-1)] for r in range(1,n-1)];width=m-2;answer=0
for top in range(max(0,n-2)):
 sums=[0]*max(0,width)
 for bottom in range(top,len(stars)):
  row=stars[bottom]
  for c in range(width):sums[c]+=row[c]
  left=0;total=0
  for right in range(width):
   total+=sums[right]
   while left<=right and total>=k:total-=sums[left];left+=1
   answer+=left
print(answer)
