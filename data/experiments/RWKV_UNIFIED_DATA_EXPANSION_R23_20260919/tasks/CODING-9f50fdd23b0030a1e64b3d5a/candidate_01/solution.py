import sys
from collections import deque
lines=iter(sys.stdin.read().splitlines());out=[];case=0
for line in lines:
 if not line.strip():continue
 n=int(line)
 if n==0:break
 duration=[]
 while len(duration)<n:duration.extend(map(int,next(lines).split()))
 graph=[[] for _ in range(n)]
 for line in lines:
  if line.strip()=='#':break
  op,a,b=line.split();a=int(a)-1;b=int(b)-1
  weight=(duration[a] if op in ('FAF','SAF') else 0)-(duration[b] if op in ('FAS','FAF') else 0)
  graph[a].append((b,weight))
 dist=[0]*n;length=[0]*n;inside=[True]*n;queue=deque(range(n));okay=True
 while queue and okay:
  u=queue.popleft();inside[u]=False
  for v,w in graph[u]:
   if dist[u]+w>dist[v]:
    dist[v]=dist[u]+w;length[v]=length[u]+1
    if length[v]>=n or (v==0 and dist[v]>0):okay=False;break
    if not inside[v]:queue.append(v);inside[v]=True
 case+=1;out.append(f'Case {case}:')
 if not okay:out.append('impossible')
 else:out.extend(f'{i+1} {t}' for i,t in enumerate(dist))
 out.append('')
print('\n'.join(out))
