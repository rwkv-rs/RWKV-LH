import sys
from fractions import Fraction as F
it=iter(map(int,sys.stdin.buffer.read().split()));out=[];case=0
for n in it:
 if not n:break
 points=[(next(it),next(it)) for _ in range(n)];segments=[(a,b) for a,b in zip(points,points[1:]) if a!=b];cuts=[set((a,b)) for a,b in segments]
 for i,(a,b) in enumerate(segments):
  rx,ry=b[0]-a[0],b[1]-a[1]
  for j in range(i):
   c,d=segments[j];sx,sy=d[0]-c[0],d[1]-c[1];qx,qy=c[0]-a[0],c[1]-a[1];den=rx*sy-ry*sx
   if den:
    t=F(qx*sy-qy*sx,den);u=F(qx*ry-qy*rx,den)
    if 0<=t<=1 and 0<=u<=1:p=(a[0]+t*rx,a[1]+t*ry);cuts[i].add(p);cuts[j].add(p)
   elif qx*ry-qy*rx==0:
    for p in (a,b,c,d):
     if min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1]) and min(c[0],d[0])<=p[0]<=max(c[0],d[0]) and min(c[1],d[1])<=p[1]<=max(c[1],d[1]):cuts[i].add(p);cuts[j].add(p)
 vertices=set(points);edges=set()
 for part in cuts:
  p=sorted(part);vertices.update(p);edges.update(zip(p,p[1:]))
 case+=1;out.append(f'Case {case}: There are {len(edges)-len(vertices)+2} pieces.')
print('\n'.join(out))
