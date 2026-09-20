import sys,functools
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];points=list(zip(v[1::2],v[2::2]));ox,oy=points[0];points=[(x-ox,y-oy) for x,y in points];base_x,base_y=points[1];lines=[(-base_y,base_x,0)]
for i in range(1,n):
 x,y=points[i];xx,yy=points[(i+1)%n];dx=xx-x;dy=yy-y;lines.append((base_y-dy,dx-base_x,dy*x-dx*y))
lo_x=min(x for x,y in points);hi_x=max(x for x,y in points);lo_y=min(y for x,y in points);hi_y=max(y for x,y in points);lines.extend(((1,0,-lo_x),(-1,0,hi_x),(0,1,-lo_y),(0,-1,hi_y)))
def half(line):
 a,b,c=line;return 0 if -a>0 or (a==0 and b>=0) else 1
def compare(l,r):
 hl=half(l);hr=half(r)
 if hl!=hr:return -1 if hl<hr else 1
 cross=l[0]*r[1]-l[1]*r[0];return -1 if cross>0 else 1 if cross<0 else 0
lines.sort(key=functools.cmp_to_key(compare));unique=[]
for line in lines:
 a,b,c=line
 if a==0 and b==0:continue
 if unique and compare(unique[-1],line)==0:
  aa,bb,cc=unique[-1]
  value=(-aa*c+cc*a)*a if a else (-bb*c+cc*b)*b
  if value>=0:unique[-1]=line
 else:unique.append(line)
def intersection(l,r):
 a,b,c=l;aa,bb,cc=r;det=a*bb-aa*b;return b*cc-bb*c,c*aa-cc*a,det
def outside(line,l,r):
 x,y,den=intersection(l,r);assert den!=0;return (line[0]*x+line[1]*y+line[2]*den)*den<0
queue=deque()
for line in unique:
 while len(queue)>1 and outside(line,queue[-2],queue[-1]):queue.pop()
 while len(queue)>1 and outside(line,queue[0],queue[1]):queue.popleft()
 queue.append(line)
while len(queue)>2 and outside(queue[0],queue[-2],queue[-1]):queue.pop()
while len(queue)>2 and outside(queue[-1],queue[0],queue[1]):queue.popleft()
region=[]
for i in range(len(queue)):
 x,y,den=intersection(queue[i],queue[(i+1)%len(queue)]);region.append((x/den,y/den))
area=abs(sum(x*region[(i+1)%len(region)][1]-y*region[(i+1)%len(region)][0] for i,(x,y) in enumerate(region)));whole=abs(sum(x*points[(i+1)%n][1]-y*points[(i+1)%n][0] for i,(x,y) in enumerate(points)));print(f'{area/whole:.4f}')
