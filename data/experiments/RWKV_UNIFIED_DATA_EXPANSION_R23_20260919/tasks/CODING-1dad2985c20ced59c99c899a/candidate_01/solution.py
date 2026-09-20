import sys,math,collections
v=list(map(int,sys.stdin.buffer.read().split()));nx,ny,width,speed,sx,sy=v[:6];heights=v[6:];n=nx*ny;g=9.80665;speed2=speed*speed
geometry={}
for dx in range(1-nx,nx):
 for dy in range(1-ny,ny):
  if dx==dy==0:continue
  events={}
  if dx:
   sign=1 if dx>0 else -1
   for k in range(abs(dx)):
    t=(k+0.5)/abs(dx);xx=sign*k;yy=t*dy;low=math.floor(yy+0.5);ys=[low]
    if abs(yy+0.5-round(yy+0.5))<1e-10:ys.append(low-1)
    events.setdefault(t,set()).update((xx+ex*sign,y) for ex in (0,1) for y in ys)
  if dy:
   sign=1 if dy>0 else -1
   for k in range(abs(dy)):
    t=(k+0.5)/abs(dy);yy=sign*k;xx=t*dx;low=math.floor(xx+0.5);xs=[low]
    if abs(xx+0.5-round(xx+0.5))<1e-10:xs.append(low-1)
    events.setdefault(t,set()).update((x,yy+ey*sign) for ey in (0,1) for x in xs)
  geometry[dx,dy]=[(t,tuple(cells)) for t,cells in events.items()]
start=(sy-1)*nx+sx-1;distance=[-1]*n;distance[start]=0;queue=collections.deque([start]);remaining=set(range(n));remaining.remove(start)
while queue:
 u=queue.popleft();ux=u%nx;uy=u//nx;z0=heights[u];reached=[]
 for w in remaining:
  dx=w%nx-ux;dy=w//nx-uy;D2=(dx*dx+dy*dy)*width*width;dz=heights[w]-z0;disc=speed2*speed2-g*(g*D2+2*dz*speed2)
  if disc<0:continue
  rise=(speed2+math.sqrt(max(0.0,disc)))/g;curve=rise-dz;ok=True
  for t,cells in geometry[dx,dy]:
   altitude=z0+rise*t-curve*t*t
   for x,y in cells:
    if altitude<=heights[(uy+y)*nx+ux+x]+1e-8:ok=False;break
   if not ok:break
  if ok:distance[w]=distance[u]+1;reached.append(w);queue.append(w)
 for w in reached:remaining.remove(w)
for y in range(ny):print(' '.join('X' if d<0 else str(d) for d in distance[y*nx:(y+1)*nx]))
