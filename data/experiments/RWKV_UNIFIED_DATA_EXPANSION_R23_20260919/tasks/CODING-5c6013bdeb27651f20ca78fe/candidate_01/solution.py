import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));n,m,start,goal,budget,snow=v[:6];start-=1;goal-=1;p=6;heights=[];limits=[]
for _ in range(n):h,l=v[p:p+2];p+=2;heights.append(h);limits.append(l)
graph=[[] for _ in range(n)]
for _ in range(m):a,b,w=v[p:p+3];p+=3;a-=1;b-=1;graph[a].append((b,w));graph[b].append((a,w))
distance=[10**100]*n;distance[start]=0;queue=[(0,start)]
while queue:
 time,u=heapq.heappop(queue)
 if time!=distance[u]:continue
 if u==goal:break
 for w,length in graph[u]:
  arrival=time+length
  if arrival>budget or arrival>=distance[w]:continue
  if w not in (start,goal) and heights[w]+snow*arrival>limits[w]:continue
  distance[w]=arrival;heapq.heappush(queue,(arrival,w))
print(distance[goal] if distance[goal]<=budget else 'wtnap wa kotori no oyatsu desu!')
