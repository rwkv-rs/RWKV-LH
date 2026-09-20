import sys,itertools
v=iter(sys.stdin.buffer.read().split());out=[];EPS=1e-9
for token in v:
 n=int(token)
 if not n:break
 top=[(float(next(v)),float(next(v))) for _ in range(n)];points=top+[(x,y-1) for x,y in top];best=top[0][0];through=(n==1)
 for (x,y),(X,Y) in itertools.combinations(points,2):
  if abs(X-x)<EPS:continue
  slope=(Y-y)/(X-x);offset=y-slope*x;previous=None;valid=True
  for j,(xx,yy) in enumerate(top):
   h=slope*xx+offset
   if yy-1-EPS<=h<=yy+EPS:previous=(xx,yy,h);continue
   valid=False
   if previous is not None:
    px,py,ph=previous;upper=h>yy;old=ph-py if upper else ph-(py-1);new=h-yy if upper else h-(yy-1);hit=px+(xx-px)*(-old)/(new-old);best=max(best,hit)
   break
  if valid:through=True;break
 out.append('Through all the pipe.' if through else f'{best:.2f}')
print('\n'.join(out))
