import sys
from fractions import Fraction as F
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def point_segment(p,a,b):
 u=sub(b,a);w=sub(p,a);length=dot(u,u)
 if not length:return F(dot(w,w))
 t=max(F(0),min(F(1),F(dot(w,u),length)));return sum((w[i]-t*u[i])**2 for i in range(3))
for case in range(v[0]):
 data=v[1+12*case:13+12*case];a,b,c,d=[tuple(data[i:i+3]) for i in range(0,12,3)];best=min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b));u=sub(b,a);z=sub(d,c);w=sub(a,c);aa=dot(u,u);bb=dot(u,z);cc=dot(z,z);dd=dot(u,w);ee=dot(z,w);det=aa*cc-bb*bb
 if det:
  s=F(bb*ee-cc*dd,det);t=F(aa*ee-bb*dd,det)
  if 0<=s<=1 and 0<=t<=1:best=min(best,sum((w[i]+s*u[i]-t*z[i])**2 for i in range(3)))
 out.append(str(best.numerator)+' '+str(best.denominator))
print('\n'.join(out))
