import sys
from fractions import Fraction as F
from functools import cmp_to_key
it=iter(map(int,sys.stdin.buffer.read().split()));m=next(it);start=(next(it),next(it));finish=(next(it),next(it));segments=[(next(it),next(it),next(it),next(it)) for _ in range(m)];cuts=[{F(0),F(1)} for _ in segments]
for i,(ax,ay,bx,by) in enumerate(segments):
 dx=bx-ax;dy=by-ay
 for j in range(i):
  cx,cy,ex,ey=segments[j];vx=ex-cx;vy=ey-cy;det=dx*vy-dy*vx
  if det:
   t=F((cx-ax)*vy-(cy-ay)*vx,det);u=F((cx-ax)*dy-(cy-ay)*dx,det)
   if 0<=t<=1 and 0<=u<=1:cuts[i].add(t);cuts[j].add(u)
  elif dx*(cy-ay)==dy*(cx-ax):
   for px,py in ((cx,cy),(ex,ey)):
    t=F(px-ax,dx) if dx else F(py-ay,dy)
    if 0<=t<=1:cuts[i].add(t)
   for px,py in ((ax,ay),(bx,by)):
    u=F(px-cx,vx) if vx else F(py-cy,vy)
    if 0<=u<=1:cuts[j].add(u)
points=[];ids={};outgoing=[];orig=[];dest=[];directions=[]
def vertex(point):
 if point not in ids:ids[point]=len(points);points.append(point);outgoing.append([])
 return ids[point]
for (ax,ay,bx,by),ts in zip(segments,cuts):
 dx=bx-ax;dy=by-ay;vertices=[vertex((ax+t*dx,ay+t*dy)) for t in sorted(ts)]
 for a,b in zip(vertices,vertices[1:]):
  h=len(orig);orig.extend((a,b));dest.extend((b,a));directions.extend(((dx,dy),(-dx,-dy)));outgoing[a].append(h);outgoing[b].append(h+1)
def compare(a,b):
 ax,ay=directions[a];bx,by=directions[b];ah=0 if ay>0 or ay==0 and ax>0 else 1;bh=0 if by>0 or by==0 and bx>0 else 1
 if ah!=bh:return ah-bh
 cross=ax*by-ay*bx;return -1 if cross>0 else 1 if cross<0 else 0
following=[0]*len(orig)
for edges in outgoing:
 edges.sort(key=cmp_to_key(compare))
 for i,h in enumerate(edges):following[h^1]=edges[i-1]
cycles=[];cycle_of=[-1]*len(orig)
for h in range(len(orig)):
 if cycle_of[h]>=0:continue
 cid=len(cycles);walk=[];e=h
 while cycle_of[e]<0:cycle_of[e]=cid;walk.append(e);e=following[e]
 polygon=[points[orig[e]] for e in walk];area=sum(points[orig[e]][0]*points[dest[e]][1]-points[dest[e]][0]*points[orig[e]][1] for e in walk);cycles.append((walk,polygon,area))
positive=[];face_of=[0]*len(cycles)
for cid,(walk,polygon,area) in enumerate(cycles):
 if area>0:
  face_of[cid]=len(positive)+1;positive.append((area,polygon,face_of[cid],min(x for x,y in polygon),max(x for x,y in polygon),min(y for x,y in polygon),max(y for x,y in polygon)))
positive.sort(key=lambda x:x[0])
def locate(point):
 x,y=point
 for area,polygon,face,x0,x1,y0,y1 in positive:
  if not (x0<x<x1 and y0<y<y1):continue
  inside=False;a=polygon[-1]
  for b in polygon:
   if (a[1]>y)!=(b[1]>y):
    cross=(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0])
    if (cross>0)==(b[1]>a[1]):inside=not inside
   a=b
  if inside:return face
 return 0
epsilon=F(1,10**60)
for cid,(walk,polygon,area) in enumerate(cycles):
 if area<=0:
  e=walk[0];a=points[orig[e]];b=points[dest[e]];dx,dy=directions[e];face_of[cid]=locate(((a[0]+b[0])/2-dy*epsilon,(a[1]+b[1])/2+dx*epsilon))
adj=[set() for _ in range(len(positive)+1)]
for e in range(0,len(orig),2):
 a=face_of[cycle_of[e]];b=face_of[cycle_of[e+1]]
 if a!=b:adj[a].add(b);adj[b].add(a)
a=locate(start);b=locate(finish);distance=[-1]*len(adj);distance[a]=0;queue=[a]
for v in queue:
 if v==b:break
 for w in adj[v]:
  if distance[w]<0:distance[w]=distance[v]+1;queue.append(w)
print(distance[b])
