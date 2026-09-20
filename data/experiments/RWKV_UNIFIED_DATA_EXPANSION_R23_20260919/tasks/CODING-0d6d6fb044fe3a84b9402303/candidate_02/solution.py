import sys
from functools import cmp_to_key
def scaled(word):
 parts=word.decode().split('.');return int(parts[0])*1000000+int((parts[1] if len(parts)>1 else '').ljust(6,'0'))
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def hull(points):
 points=sorted(set(points))
 if len(points)<2:return points
 lower=[];upper=[]
 for p in points:
  while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
  lower.append(p)
 for p in reversed(points):
  while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
  upper.append(p)
 return lower[:-1]+upper[:-1]
v=sys.stdin.buffer.read().split();m,n=map(int,v[:2]);p=2;raw=[];target=[]
for i in range(m+n):
 point=(scaled(v[p]),scaled(v[p+1]));p+=3
 (raw if i<m else target).append(point)
raw=sorted(set(raw));target=hull(target);m=len(raw);h=len(target)
if h==1 and target[0] in raw:print(1);raise SystemExit
if h<=2:
 for i,a in enumerate(raw):
  for b in raw[:i]:
   if all(cross(a,b,q)==0 and min(a[0],b[0])<=q[0]<=max(a[0],b[0]) and min(a[1],b[1])<=q[1]<=max(a[1],b[1]) for q in target):print(2);raise SystemExit
def compare(a,b):
 ha=(a[1]<0 or (a[1]==0 and a[0]<0));hb=(b[1]<0 or (b[1]==0 and b[0]<0))
 if ha!=hb:return 1 if ha else -1
 c=a[0]*b[1]-a[1]*b[0]
 return -1 if c>0 else 1 if c<0 else 0
adj=[0]*m;centre=(sum(x for x,y in target),sum(y for x,y in target))
for i,a in enumerate(raw):
 directions=[(b[0]-a[0],b[1]-a[1],j) for j,b in enumerate(raw) if i!=j];directions.sort(key=cmp_to_key(compare))
 if not directions:continue
 dx,dy,_=directions[0];at=min(range(h),key=lambda k:dx*target[k][1]-dy*target[k][0])
 previous=None
 for dx,dy,j in directions:
  if previous is not None and (previous[0]*dy-previous[1]*dx<0 or (previous[0]*dy-previous[1]*dx==0 and previous[0]*dx+previous[1]*dy<0)):at=min(range(h),key=lambda k:dx*target[k][1]-dy*target[k][0])
  previous=(dx,dy)
  for step in range(h-1):
   nxt=(at+1)%h
   if dx*target[nxt][1]-dy*target[nxt][0]<=dx*target[at][1]-dy*target[at][0]:at=nxt
   else:break
  if dx*(target[at][1]-a[1])-dy*(target[at][0]-a[0])<0:continue
  if dx*(centre[1]-h*a[1])-dy*(centre[0]-h*a[0])<=0:continue
  adj[i]|=1<<j
best=m+1
for start in range(m):
 front=adj[start];seen=1<<start;distance=1
 while front and distance<best:
  if front>>start&1:best=distance;break
  seen|=front;following=0
  while front:
   bit=front&-front;front^=bit;following|=adj[bit.bit_length()-1]
  front=following&~(seen^(1<<start));distance+=1
 if best==3:break
print(best if best<=m else -1)
