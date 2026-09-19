import sys
from decimal import Decimal,localcontext,ROUND_CEILING,ROUND_HALF_UP
out=[]
for token in sys.stdin.read().split():
 n=int(token)
 with localcontext() as ctx:
  ctx.prec=max(50,len(token)+30);z=Decimal(n)*(Decimal(2).ln()/Decimal(10).ln());e=int(z.to_integral_value(rounding=ROUND_CEILING));mantissa=(Decimal(10)**(Decimal(e)-z)).quantize(Decimal('.001'),rounding=ROUND_HALF_UP)
  if mantissa==10:mantissa=Decimal('1.000');e-=1
  out.append(f'2^-{n} = {mantissa:.3f}E-{e}')
print('\n'.join(out))
