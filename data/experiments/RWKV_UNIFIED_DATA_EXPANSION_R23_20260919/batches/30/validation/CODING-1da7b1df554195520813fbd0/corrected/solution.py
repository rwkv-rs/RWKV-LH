import sys,math
v=iter(map(int,sys.stdin.read().split()));n=next(v);h=next(v);w=next(v);radius=next(v);points=[(next(v),next(v)) for _ in range(n)];h-=2*radius;w-=2*radius
if h<0 or w<0:print('No');raise SystemExit
period=math.pi;events=[];active=0
for i,(x,y) in enumerate(points):
 for xx,yy in points[i+1:]:
  dx=xx-x;dy=yy-y;distance=math.hypot(dx,dy)
  if not distance:continue
  angle=math.atan2(dy,dx)
  for width,center in ((w,-angle),(h,math.pi/2-angle)):
   if width>=distance:continue
   delta=math.acos(width/distance);left=(center-delta)%period;right=(center+delta)%period
   if left<right:events.extend(((left,1),(right,-1)))
   else:active+=1;events.extend(((right,-1),(left,1)))
previous=0.0;possible=False
for position,change in sorted(events):
 if active==0 and position-previous>1e-12:possible=True;break
 active+=change;previous=position
if active==0 and period-previous>1e-12:possible=True
print('Yes' if possible else 'No')
