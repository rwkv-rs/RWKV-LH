import sys,math
v=iter(sys.stdin.read().replace(',',' ').split());out=[];tau=2*math.pi
while True:
 try:n=int(next(v))
 except StopIteration:break
 if not n:break
 points=[(float(next(v)),float(next(v))) for _ in range(n)];best=1
 for i,(x,y) in enumerate(points):
  events=[];base=1
  for j,(xx,yy) in enumerate(points):
   if i==j:continue
   dx=xx-x;dy=yy-y;dist=math.hypot(dx,dy)
   if dist>2+1e-10:continue
   if dist<1e-12:base+=1;continue
   angle=math.atan2(dy,dx)%tau;delta=math.acos(min(1,dist/2));lo=(angle-delta)%tau;hi=(angle+delta)%tau
   if lo<=hi:events.extend([(lo,-1),(hi,1)])
   else:base+=1;events.extend([(hi,1),(lo,-1)])
  count=base;best=max(best,count)
  for angle,kind in sorted(events):
   count-=kind;best=max(best,count)
 out.append(str(best))
print('\n'.join(out))
