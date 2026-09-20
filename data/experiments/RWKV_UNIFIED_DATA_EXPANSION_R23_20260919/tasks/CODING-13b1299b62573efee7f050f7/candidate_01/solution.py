import sys
from collections import deque
sys.setrecursionlimit(30000)
v=sys.stdin.buffer.read().split();n,m=map(int,v[:2]);grid=v[2:];left=[];right=[];adj={};reverse={}
for i in range(n):
 for j in range(m):
  if grid[i][j]==46:
   u=i*m+j
   if (i+j)%2==0:left.append(u);adj[u]=[]
   else:right.append(u);reverse[u]=[]
for u in left:
 i,j=divmod(u,m)
 for a,b in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
  if 0<=a<n and 0<=b<m and grid[a][b]==46:w=a*m+b;adj[u].append(w);reverse[w].append(u)
match={};distance={}
while True:
 q=deque();found=False
 for u in left:
  distance[u]=-1
  if u not in match:distance[u]=0;q.append(u)
 while q:
  u=q.popleft()
  for w in adj[u]:
   if w not in match:found=True
   elif distance[match[w]]<0:distance[match[w]]=distance[u]+1;q.append(match[w])
 if not found:break
 def augment(u):
  for w in adj[u]:
   if w not in match or (distance[match[w]]==distance[u]+1 and augment(match[w])):match[u]=w;match[w]=u;return True
  distance[u]=-1;return False
 for u in left:
  if u not in match:augment(u)
winners=set()
for side,graph in ((left,adj),(right,reverse)):
 visited={u for u in side if u not in match};q=list(visited)
 for u in q:
  for w in graph[u]:
   if match.get(u)==w:continue
   if w in match:
    z=match[w]
    if z not in visited:visited.add(z);q.append(z)
 winners.update(visited)
if not winners:print('LOSE')
else:
 print('WIN')
 for u in sorted(winners):i,j=divmod(u,m);print(i+1,j+1)
