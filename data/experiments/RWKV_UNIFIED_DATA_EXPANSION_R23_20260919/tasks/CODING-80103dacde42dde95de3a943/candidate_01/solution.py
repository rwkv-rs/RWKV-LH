import sys
from decimal import Decimal,localcontext,ROUND_HALF_UP
values=sys.stdin.read().split()
with localcontext() as context:
 context.prec=max(50,sum(map(len,values))+20);a,b=map(Decimal,values);answer=a*b/(a+b);print(format(answer.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),'.2f'))
