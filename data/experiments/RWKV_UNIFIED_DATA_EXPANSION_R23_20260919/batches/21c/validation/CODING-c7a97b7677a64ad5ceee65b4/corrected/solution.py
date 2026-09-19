import sys
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_HALF_UP
v=iter(sys.stdin.read().split());n=int(next(v));points=[[Fraction(next(v)) for j in range(n)] for i in range(n+1)];base=points[0];base2=sum(x*x for x in base);matrix=[]
for p in points[1:]:matrix.append([2*(p[j]-base[j]) for j in range(n)]+[sum(x*x for x in p)-base2])
for col in range(n):
 pivot=next(i for i in range(col,n) if matrix[i][col]);matrix[col],matrix[pivot]=matrix[pivot],matrix[col];div=matrix[col][col];matrix[col]=[x/div for x in matrix[col]]
 for i in range(n):
  if i!=col:
   factor=matrix[i][col]
   if factor:matrix[i]=[a-factor*b for a,b in zip(matrix[i],matrix[col])]
out=[]
with localcontext() as ctx:
 ctx.prec=80
 for row in matrix:
  x=row[-1];d=(Decimal(x.numerator)/Decimal(x.denominator)).quantize(Decimal('.001'),rounding=ROUND_HALF_UP)
  if d==0:d=abs(d)
  out.append(f'{d:.3f}')
print(' '.join(out))
