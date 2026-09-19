import sys,math
from fractions import Fraction
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);lines=[];pieces=1
 for _ in range(n):
  x,y,u,v=[next(it) for j in range(4)];a=y-v;b=u-x;c=x*v-u*y;g=math.gcd(math.gcd(abs(a),abs(b)),abs(c));a//=g;b//=g;c//=g
  if a<0 or (a==0 and b<0):a=-a;b=-b;c=-c
  line=(a,b,c)
  if line in lines:continue
  points=set()
  for d,e,f in lines:
   det=a*e-b*d
   if det:
    xx=Fraction(b*f-c*e,det);yy=Fraction(c*d-a*f,det)
    if 0<xx<1000 and 0<yy<1000:points.add((xx,yy))
  pieces+=1+len(points);lines.append(line)
 out.append(str(pieces))
print('\n\n'.join(out))
