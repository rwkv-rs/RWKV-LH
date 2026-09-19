import sys,math
from collections import Counter
v=iter(map(int,sys.stdin.read().split()));n=next(v);points=[(next(v),next(v)) for _ in range(n)];collinear=0
for i,(x,y) in enumerate(points):
 slopes=Counter()
 for xx,yy in points[i+1:]:
  dx=xx-x;dy=yy-y;g=math.gcd(dx,dy);dx//=g;dy//=g
  if dx<0 or dx==0 and dy<0:dx=-dx;dy=-dy
  slopes[dx,dy]+=1
 collinear+=sum(c*(c-1)//2 for c in slopes.values())
print(n*(n-1)*(n-2)//6-collinear)
