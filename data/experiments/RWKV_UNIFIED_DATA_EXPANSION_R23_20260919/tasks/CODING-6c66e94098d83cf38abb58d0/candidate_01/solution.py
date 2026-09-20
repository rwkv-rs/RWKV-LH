import sys,heapq
from collections import deque
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);priority=[next(v) for _ in range(n)];g=[[] for _ in range(n)]
for _ in range(n-1):
 a=next(v)-1;b=next(v)-1;c=next(v);g[a].append((b,c));g[b].append((a,c))
parent=[-1]*n;capacity=[0]*n;children=[[] for _ in range(n)];order=[0]
for u in order:
 for w,c in g[u]:
  if w!=parent[u]:parent[w]=u;capacity[w]=c;children[u].append(w);order.append(w)
records=[None]*n
for u in reversed(order[1:]):
 cs=children[u];cap=capacity[u]
 if not cs:records[u]=(deque([(1,priority[u],u)]),0,1);continue
 if len(cs)==1 and records[cs[0]][2]<=cap:
  events,offset,peak=records[cs[0]];records[cs[0]]=None;events.appendleft((-offset,priority[u],u));records[u]=(events,offset+1,peak);continue
 events=[(0,priority[u],u)]
 for child in cs:
  stream,offset,_=records[child];events.extend((t+offset,p,i) for t,p,i in stream);records[child]=None
 events.sort();at=0;day=0;queue=[];out=deque();peak=0
 while at<len(events) or queue:
  if not queue:day=max(day,events[at][0])
  while at<len(events) and events[at][0]<=day:
   _,p,i=events[at];heapq.heappush(queue,(p,i));at+=1
  count=min(cap,len(queue));peak=max(peak,count)
  for _ in range(count):
   p,i=heapq.heappop(queue);out.append((day+1,p,i))
  day+=1
 records[u]=(out,0,peak)
answer=[0]*n
for child in children[0]:
 stream,offset,_=records[child]
 for t,p,i in stream:answer[i]=t+offset
print(' '.join(map(str,answer)))
