import sys
from fractions import Fraction
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];p=list(zip(v[1::2],v[2::2]));area=moment=0
for i in range(n):
 x,y=p[i];u,w=p[(i+1)%n];cross=x*w-y*u;area+=cross;moment+=(x+u)*cross
if area<0:area=-area;moment=-moment
support=[x for x,y in p if y==0];L=min(support);R=max(support);x=p[0][0];lo=Fraction(0);hi=None;valid=True
for coef,rhs in [(6*(x-L),3*L*area-moment),(6*(R-x),moment-3*R*area)]:
 if coef>0:lo=max(lo,Fraction(rhs,coef))
 elif coef<0:
  bound=Fraction(rhs,coef);hi=bound if hi is None else min(hi,bound)
 elif rhs>0:valid=False
if not valid or (hi is not None and hi<lo):print('unstable')
else:print(f'{lo.numerator//lo.denominator} .. '+('inf' if hi is None else str(-(-hi.numerator//hi.denominator))))
