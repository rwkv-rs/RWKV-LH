import sys
v=iter(map(int,sys.stdin.read().split()));n=next(v);polygons=[]
for _ in range(n):polygons.append([(next(v),next(v)) for i in range(next(v))])
result=polygons[0]
for polygon in polygons[1:]:
 for i,a in enumerate(polygon):
  b=polygon[(i+1)%len(polygon)];dx=b[0]-a[0];dy=b[1]-a[1]
  def side(p):return dx*(p[1]-a[1])-dy*(p[0]-a[0])
  clipped=[]
  if not result:break
  previous=result[-1];old=side(previous)
  for current in result:
   value=side(current);inside=value>=-1e-9;was_inside=old>=-1e-9
   if inside!=was_inside:
    t=old/(old-value);clipped.append((previous[0]+t*(current[0]-previous[0]),previous[1]+t*(current[1]-previous[1])))
   if inside:clipped.append(current)
   previous=current;old=value
  result=clipped
area=abs(sum(p[0]*result[(i+1)%len(result)][1]-p[1]*result[(i+1)%len(result)][0] for i,p in enumerate(result)))/2
print(f'{area:.3f}')
