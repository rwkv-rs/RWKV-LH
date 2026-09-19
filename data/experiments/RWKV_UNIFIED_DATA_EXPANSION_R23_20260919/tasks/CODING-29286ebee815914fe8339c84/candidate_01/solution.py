import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);k=next(it);casters=[tuple(next(it) for _ in range(4)) for _ in range(n)];targets=[(next(it),next(it)) for _ in range(m)];trees=[(next(it),next(it),next(it)) for _ in range(k)];available=[[] for _ in range(n)];covered=set()
for i,(x,y,r,t) in enumerate(casters):
 for j,(u,v) in enumerate(targets):
  dx=u-x;dy=v-y;length=dx*dx+dy*dy
  if length>r*r:continue
  blocked=False
  for a,b,radius in trees:
   ax=a-x;ay=b-y;projection=ax*dx+ay*dy
   if projection<=0:hit=ax*ax+ay*ay<=radius*radius
   elif projection>=length:hit=(a-u)**2+(b-v)**2<=radius*radius
   else:hit=(ax*dy-ay*dx)**2<=radius*radius*length
   if hit:blocked=True;break
  if not blocked:available[i].append(j);covered.add(j)
if len(covered)!=m:print(-1);raise SystemExit
if m==0:print(0);raise SystemExit
source=n+m;sink=source+1;size=sink+1
def feasible(time):
 g=[[] for _ in range(size)]
 def add(x,y,cap):g[x].append([y,cap,len(g[y])]);g[y].append([x,0,len(g[x])-1])
 for i,caster in enumerate(casters):
  delay=caster[3];add(source,i,min(m,time//delay+1) if delay else m)
  for j in available[i]:add(i,n+j,1)
 for j in range(m):add(n+j,sink,1)
 flow=0
 while True:
  level=[-1]*size;level[source]=0;queue=deque([source])
  while queue:
   x=queue.popleft()
   for y,cap,rev in g[x]:
    if cap and level[y]<0:level[y]=level[x]+1;queue.append(y)
  if level[sink]<0:return False
  pointer=[0]*size
  def send(x,amount):
   if x==sink:return amount
   while pointer[x]<len(g[x]):
    edge=g[x][pointer[x]];y,cap,rev=edge
    if cap and level[y]==level[x]+1:
     pushed=send(y,min(amount,cap))
     if pushed:edge[1]-=pushed;g[y][rev][1]+=pushed;return pushed
    pointer[x]+=1
   return 0
  while True:
   pushed=send(source,m-flow)
   if not pushed:break
   flow+=pushed
   if flow==m:return True
lo=0;hi=(m-1)*max(t for x,y,r,t in casters)
while lo<hi:
 mid=(lo+hi)//2
 if feasible(mid):hi=mid
 else:lo=mid+1
print(lo)
