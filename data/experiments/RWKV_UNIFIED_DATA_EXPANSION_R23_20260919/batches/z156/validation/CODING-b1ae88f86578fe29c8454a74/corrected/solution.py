import sys,math
v=iter(sys.stdin.buffer.read().split());tracks=[]
for _ in range(2):
 x=int(next(v));y=int(next(v));m=int(next(v));points=[]
 for _ in range(m):
  d=int(next(v));axis=next(v);sign=(d>0)-(d<0)
  for _ in range(abs(d)):
   points.append((x,y))
   if axis==b'X':x+=sign
   else:y+=sign
 tracks.append(points)
a,b=tracks;g=math.gcd(len(a),len(b));groups=[[] for _ in range(g)]
for i,p in enumerate(b):groups[i%g].append(p)

def build(points):
 xmin=min(x for x,y in points);xmax=max(x for x,y in points);ymin=min(y for x,y in points);ymax=max(y for x,y in points)
 if len(points)<=8:return (xmin,xmax,ymin,ymax,points,None,None)
 axis=int(ymax-ymin>xmax-xmin);points.sort(key=lambda p:p[axis]);mid=len(points)//2
 return (xmin,xmax,ymin,ymax,None,build(points[:mid]),build(points[mid:]))
def lower(node,x,y):
 xmin,xmax,ymin,ymax=node[:4];dx=max(xmin-x,0,x-xmax);dy=max(ymin-y,0,y-ymax);return dx*dx+dy*dy
roots=[build(list(set(group))) for group in groups];best=10**30
for residue in range(g):
 root=roots[residue]
 for x,y in set(a[residue::g]):
  stack=[root]
  while stack:
   node=stack.pop()
   if lower(node,x,y)>=best:continue
   points=node[4]
   if points is not None:
    for u,v in points:
     distance=(u-x)**2+(v-y)**2
     if distance<best:best=distance
   else:
    left,right=node[5:];ld=lower(left,x,y);rd=lower(right,x,y)
    if ld<rd:
     if rd<best:stack.append(right)
     if ld<best:stack.append(left)
    else:
     if ld<best:stack.append(left)
     if rd<best:stack.append(right)
  if best==0:break
 if best==0:break
print(f'{math.sqrt(best):.2f}')
