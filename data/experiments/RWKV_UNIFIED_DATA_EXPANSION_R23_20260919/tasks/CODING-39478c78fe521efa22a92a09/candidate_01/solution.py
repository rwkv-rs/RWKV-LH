import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));m=next(it);n=next(it);board=[[-1]*m for _ in range(m)]
for _ in range(n):x=next(it)-1;y=next(it)-1;board[x][y]=next(it)
dist={ (0,0,board[0][0]):0 };queue=[(0,0,0,board[0][0])];answer=-1
while queue:
 cost,x,y,color=heapq.heappop(queue)
 if dist[(x,y,color)]!=cost:continue
 if x==m-1 and y==m-1:answer=cost;break
 for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
  u=x+dx;v=y+dy
  if not(0<=u<m and 0<=v<m):continue
  nextcolor=board[u][v]
  if nextcolor<0:
   if board[x][y]<0:continue
   nextcolor=color;extra=2
  else:extra=int(nextcolor!=color)
  new=cost+extra;state=(u,v,nextcolor)
  if new<dist.get(state,10**18):dist[state]=new;heapq.heappush(queue,(new,u,v,nextcolor))
print(answer)
