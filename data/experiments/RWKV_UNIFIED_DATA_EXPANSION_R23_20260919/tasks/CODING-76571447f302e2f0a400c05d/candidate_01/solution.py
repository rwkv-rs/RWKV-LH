import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];sx,sy,fx,fy=v[2:6];points=[tuple(v[6+2*i:8+2*i]) for i in range(m)];g=[[] for _ in range(m)]
for axis in (0,1):
 order=sorted(range(m),key=lambda i:points[i][axis])
 for i,j in zip(order,order[1:]):
  weight=points[j][axis]-points[i][axis];g[i].append((j,weight));g[j].append((i,weight))
distance=[min(abs(x-sx),abs(y-sy)) for x,y in points];queue=[(d,i) for i,d in enumerate(distance)];heapq.heapify(queue);answer=abs(fx-sx)+abs(fy-sy)
while queue:
 d,i=heapq.heappop(queue)
 if d!=distance[i]:continue
 x,y=points[i];answer=min(answer,d+abs(x-fx)+abs(y-fy))
 for j,w in g[i]:
  candidate=d+w
  if candidate<distance[j]:distance[j]=candidate;heapq.heappush(queue,(candidate,j))
print(answer)
