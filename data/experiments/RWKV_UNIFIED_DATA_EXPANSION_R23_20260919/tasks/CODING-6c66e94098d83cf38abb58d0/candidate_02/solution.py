import sys,heapq
from collections import deque
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);priority=[next(v) for _ in range(n)];ranking={p:i for i,p in enumerate(sorted(priority))};keys=[(ranking[p]<<13)|i for i,p in enumerate(priority)];g=[[] for _ in range(n)];MASK=(1<<26)-1
for _ in range(n-1):
 a=next(v)-1;b=next(v)-1;c=next(v);g[a].append((b,c));g[b].append((a,c))
parent=[-1]*n;capacity=[0]*n;children=[[] for _ in range(n)];order=[0]
for u in order:
 for w,c in g[u]:
  if w!=parent[u]:parent[w]=u;capacity[w]=c;children[u].append(w);order.append(w)
records=[None]*n
for u in reversed(order[1:]):
 cs=children[u];cap=capacity[u]
 if not cs:records[u]=(deque([(1<<26)|keys[u]]),0,1);continue
 if len(cs)==1 and records[cs[0]][2]<=cap:
  events,offset,peak=records[cs[0]];records[cs[0]]=None;events.appendleft((-offset<<26)+keys[u]);records[u]=(events,offset+1,peak);continue
 events=[keys[u]]
 for child in cs:
  stream,offset,_=records[child];delta=offset<<26;events.extend(t+delta for t in stream);records[child]=None
 events.sort();at=0;day=0;queue=[];out=deque();peak=0;size=len(events);push=heapq.heappush;pop=heapq.heappop;pushpop=heapq.heappushpop;append=out.append
 while at<size or queue:
  if not queue:day=max(day,events[at]>>26)
  first=at;bound=(day+1)<<26
  while at<size and events[at]<bound:at+=1
  if cap==1 and at-first==1:
   item=events[first]&MASK
   if queue:item=pushpop(queue,item)
   append(bound|item);peak=1;day+=1;continue
  for j in range(first,at):push(queue,events[j]&MASK)
  count=min(cap,len(queue));peak=max(peak,count)
  for _ in range(count):append(bound|pop(queue))
  day+=1
 records[u]=(out,0,peak)
answer=[0]*n
for child in children[0]:
 stream,offset,_=records[child]
 for event in stream:answer[event&8191]=(event>>26)+offset
print(' '.join(map(str,answer)))
