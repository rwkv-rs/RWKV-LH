import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);points=[(next(it),next(it),next(it)) for _ in range(n)];groups={};answer=-1
for i,(x,y,c) in enumerate(points):
 for X,Y,C in points[:i]:
  dx,dy=x-X,y-Y;g=math.gcd(dx,dy);dx//=g;dy//=g
  if dx<0 or (dx==0 and dy<0):dx=-dx;dy=-dy
  sx,sy=x+X,y+Y;key=(dx,dy,sx*dx+sy*dy);line=sx*dy-sy*dx;weight=c+C
  if key not in groups:groups[key]=(weight,line)
  else:
   best,where=groups[key]
   if where!=line:answer=max(answer,best+weight)
   if weight>best:groups[key]=(weight,line)
print(answer)
