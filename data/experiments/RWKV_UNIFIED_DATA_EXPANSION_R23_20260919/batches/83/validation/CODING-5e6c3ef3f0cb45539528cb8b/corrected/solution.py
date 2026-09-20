import sys
from array import array
from collections import deque
v=sys.stdin.buffer.read().split();n,m=map(int,v[:2]);length=array('i',[0]);link=array('i',[-1]);edges=[array('i',[-1]) for _ in range(3)];last=0
for text in v[2:2+m]:
 for c in (*text,50):
  c-=48;cur=len(length);length.append(length[last]+1);link.append(0)
  for edge in edges:edge.append(-1)
  p=last
  while p>=0 and edges[c][p]<0:edges[c][p]=cur;p=link[p]
  if p>=0:
   q=edges[c][p]
   if length[p]+1==length[q]:link[cur]=q
   else:
    clone=len(length);length.append(length[p]+1);link.append(link[q])
    for edge in edges:edge.append(edge[q])
    while p>=0 and edges[c][p]==q:edges[c][p]=clone;p=link[p]
    link[q]=link[cur]=clone
  last=cur
out=[]
for text in v[2+m:2+m+n]:
 matched=[0];state=0;current=0
 for c in text:
  c-=48
  while state and edges[c][state]<0:state=link[state];current=length[state]
  if edges[c][state]>=0:state=edges[c][state];current+=1
  else:current=0
  matched.append(current)
 size=len(text)
 def feasible(minimum):
  dp=[0]*(size+1);queue=deque()
  for i in range(1,size+1):
   j=i-minimum
   if j>=0:
    score=dp[j]-j
    while queue and dp[queue[-1]]-queue[-1]<=score:queue.pop()
    queue.append(j)
   start=i-matched[i]
   while queue and queue[0]<start:queue.popleft()
   dp[i]=dp[i-1]
   if queue:dp[i]=max(dp[i],i+dp[queue[0]]-queue[0])
  return dp[size]*10>=9*size
 lo=0;hi=max(matched)+1
 while lo+1<hi:
  mid=(lo+hi)//2
  if feasible(mid):lo=mid
  else:hi=mid
 out.append(str(lo))
print('\n'.join(out))
