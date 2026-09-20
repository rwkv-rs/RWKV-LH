import sys
from fractions import Fraction as F
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];p=list(zip(v[1::2],v[2::2]));cross=moment=0
for (x,y),(X,Y) in zip(p,p[1:]+p[:1]):z=x*Y-X*y;cross+=z;moment+=(x+X)*z
if cross<0:cross=-cross;moment=-moment
area=F(cross,2);moment=F(moment,6);L=min(x for x,y in p if y==0);R=max(x for x,y in p if y==0);attach=p[0][0];low=F(0);high=None;valid=True
for a,b in ((L-attach,moment-L*area),(attach-R,R*area-moment)):
 if a==0:
  if b<0:valid=False
 elif a>0:
  bound=b/a;high=bound if high is None else min(high,bound)
 else:low=max(low,b/a)
if not valid or (high is not None and high<low):print('unstable')
else:
 upper='inf' if high is None else str(-((-high.numerator)//high.denominator));print(f'{low.numerator//low.denominator} .. {upper}')
