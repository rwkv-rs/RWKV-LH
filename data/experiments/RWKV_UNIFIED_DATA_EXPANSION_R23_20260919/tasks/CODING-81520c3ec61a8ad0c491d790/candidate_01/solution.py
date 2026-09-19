import sys
from decimal import Decimal,localcontext
n=int(sys.stdin.read())
with localcontext() as context:
 context.prec=50;answer=Decimal(n*(n+1))/Decimal(2*(2*n-1));print(format(answer,'.9f'))
