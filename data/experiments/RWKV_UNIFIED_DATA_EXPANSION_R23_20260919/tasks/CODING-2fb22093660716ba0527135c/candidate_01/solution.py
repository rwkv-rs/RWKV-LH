import sys
from collections import deque
stream=iter(sys.stdin);tests=int(next(stream));out=[]
for _ in range(tests):
 line=next(stream).strip()
 while not line:line=next(stream).strip()
 names=[name.strip() for name in line.split(':',1)[1].split(',')];index={name:i for i,name in enumerate(names)};count=len(names);line_names=[name.strip() for name in next(stream).split(':',1)[1].split(',')];routes=[];incident=[[] for _ in names]
 for j in range(len(line_names)):
  stops=[index[name.strip()] for name in next(stream).split(':',1)[1].split(',')];routes.append(stops)
  for u in stops:incident[u].append(j)
 start_name=next(stream).strip().removeprefix('Johny lives at ');finish_name=next(stream).strip().removeprefix('Michelle lives at ');start=index[start_name];finish=index[finish_name];distance=[-1]*count;distance[start]=0;queue=deque([start]);used=[False]*len(routes);ordered=[]
 while queue:
  u=queue.popleft()
  for j in incident[u]:
   if used[j]:continue
   used[j]=True;level=distance[u];ordered.append((level,j))
   for w in routes[j]:
    if distance[w]<0:distance[w]=level+1;queue.append(w)
 best=[-10**18]*count;best[start]=0
 for level,j in ordered:
  stops=routes[j];running=-10**18
  for position,u in enumerate(stops):
   if distance[u]==level:running=max(running,best[u]-position)
   elif distance[u]==level+1:best[u]=max(best[u],running+position)
  running=-10**18
  for position in range(len(stops)-1,-1,-1):
   u=stops[position]
   if distance[u]==level:running=max(running,best[u]+position)
   elif distance[u]==level+1:best[u]=max(best[u],running-position)
 boards=distance[finish];minutes=best[finish];out.append(f"optimal travel from {start_name} to {finish_name}: {boards} {'line' if boards==1 else 'lines'}, {minutes} {'minute' if minutes==1 else 'minutes'}")
print('\n'.join(out))
