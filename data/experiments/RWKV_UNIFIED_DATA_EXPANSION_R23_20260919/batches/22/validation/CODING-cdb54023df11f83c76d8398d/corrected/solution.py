import sys,math
v=iter(sys.stdin.read().split());out=[]
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
for _ in range(int(next(v))):
 points=[];area=0.
 for j in range(int(next(v))):
  x=float(next(v));y=float(next(v));w=float(next(v));h=float(next(v));angle=math.radians(float(next(v)));c=math.cos(angle);s=math.sin(angle);area+=w*h
  for dx in (-w/2,w/2):
   for dy in (-h/2,h/2):points.append((x+dx*c+dy*s,y-dx*s+dy*c))
 points=sorted(set(points));lower=[];upper=[]
 for p in points:
  while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
  lower.append(p)
 for p in reversed(points):
  while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
  upper.append(p)
 hull=lower[:-1]+upper[:-1];twice=abs(sum(hull[i][0]*hull[(i+1)%len(hull)][1]-hull[i][1]*hull[(i+1)%len(hull)][0] for i in range(len(hull))))
 out.append(f'{200*area/twice:.1f} %')
print('\n'.join(out))
