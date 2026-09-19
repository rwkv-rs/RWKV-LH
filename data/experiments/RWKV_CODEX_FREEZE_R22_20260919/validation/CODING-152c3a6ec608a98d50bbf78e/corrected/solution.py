import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for case in range(1,t+1):
 n=next(it);m=next(it);br=next(it)-1;bc=next(it)-1;a=[[next(it) for _ in range(m)] for _ in range(n)];dist=[[1000000]*m for _ in range(n)];dist[br][bc]=0;heap=[(0,br,bc)];answer=None
 while heap:
  cost,r,c=heapq.heappop(heap)
  if cost!=dist[r][c]:continue
  if r in (0,n-1) or c in (0,m-1):answer=cost;break
  for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
   if 0<=rr<n and 0<=cc<m and a[rr][cc]>=a[r][c]:
    candidate=max(cost,a[rr][cc]-a[r][c])
    if candidate<dist[rr][cc]:dist[rr][cc]=candidate;heapq.heappush(heap,(candidate,rr,cc))
 out.append(f'{case}. '+('IMPOSSIBLE' if answer is None else str(answer)))
print('\n'.join(out))
