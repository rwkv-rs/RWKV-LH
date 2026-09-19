import sys
from fractions import Fraction
out=[]
for n in map(int,sys.stdin.read().split()):
 value=sum((Fraction(n,i) for i in range(1,n+1)),Fraction());whole,remainder=divmod(value.numerator,value.denominator)
 if not remainder:out.append(str(whole))
 else:
  width=len(str(value.denominator));prefix=' '*(len(str(whole))+1);out.extend((prefix+str(remainder).rjust(width),str(whole)+' '+'-'*width,prefix+str(value.denominator)))
print('\n'.join(out))
