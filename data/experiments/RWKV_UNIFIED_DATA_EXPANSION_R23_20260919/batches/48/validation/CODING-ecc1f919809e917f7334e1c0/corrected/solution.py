import sys
from decimal import Decimal as D
lines=iter(sys.stdin.read().splitlines());figures=[]
for line in lines:
 v=line.split()
 if not v:continue
 if v[0]=='*':break
 figures.append((v[0],list(map(D,v[1:]))))
out=[];index=0
for line in lines:
 v=line.split()
 if not v:continue
 x,y=map(D,v)
 if x==D('9999.9') and y==D('9999.9'):break
 index+=1;found=False
 for j,(kind,p) in enumerate(figures,1):
  if kind=='r':a,b,c,d=p;inside=min(a,c)<x<max(a,c) and min(b,d)<y<max(b,d)
  else:a,b,r=p;inside=(x-a)**2+(y-b)**2<r*r
  if inside:found=True;out.append(f'Point {index} is contained in figure {j}')
 if not found:out.append(f'Point {index} is not contained in any figure')
print('\n'.join(out))
