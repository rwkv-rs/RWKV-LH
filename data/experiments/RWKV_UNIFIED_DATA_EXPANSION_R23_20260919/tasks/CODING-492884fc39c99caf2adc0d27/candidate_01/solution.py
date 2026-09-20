import sys
from array import array
v=sys.stdin.buffer.read().split();n=int(v[0]);children=[[] for _ in range(n+1)]
for i in range(1,n+1):children[int(v[2*i-1])].append((v[2*i],i))
k=int(v[2*n+1]);selected=list(map(int,v[2*n+2:]));marked=bytearray(n+1)
for u in selected:marked[u]=1
answer=array('i',[0])*(n+1);rank=0;stack=[(0,0,0)]
while stack:
 u,d,best=stack.pop();start=rank
 if marked[u]:d=min(d,rank+1+best)
 answer[u]=d;best=min(best,d-start)
 if marked[u]:rank+=1
 for c,w in sorted(children[u],reverse=True):stack.append((w,d+1,best))
print(*(answer[u] for u in selected))
