import sys
from fractions import Fraction
out=[]
for s in sys.stdin.read().split():
 if s=='END':break
 f=Fraction(s);a=f.numerator;b=f.denominator;seen=set();ok=True
 while a not in (0,b) and a not in seen:
  seen.add(a);a*=3
  if b<=a<2*b:
   ok=(a==b);break
  if a>=2*b:a-=2*b
 out.append('MEMBER' if ok else 'NON-MEMBER')
print('\n'.join(out))
