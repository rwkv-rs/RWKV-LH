import sys
from decimal import Decimal,getcontext
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);cells=[(0,0)];corners={(0,0),(0,1),(1,0),(1,1)};steps=((-1,0),(0,-1),(1,0),(0,1))
for i in range(1,n):
 parent=next(v);direction=next(v);x,y=cells[parent];dx,dy=steps[direction];x+=dx;y+=dy;cells.append((x,y));corners.update(((x,y),(x+1,y),(x,y+1),(x+1,y+1)))
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
ordered=sorted(corners);lower=[];upper=[]
for p in ordered:
 while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
 lower.append(p)
for p in reversed(ordered):
 while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
 upper.append(p)
hull=lower[:-1]+upper[:-1];h=len(hull);best_num=None;best_den=1
for i,(x,y) in enumerate(hull):
 u,v=hull[(i+1)%h];dx=u-x;dy=v-y
 def dot(j):a,b=hull[j];return a*dx+b*dy
 def normal(j):a,b=hull[j];return a*dy-b*dx
 if i==0:
  hi=max(range(h),key=dot);lo=min(range(h),key=dot);far=min(range(h),key=normal)
 else:
  while dot((hi+1)%h)>dot(hi):hi=(hi+1)%h
  while dot((lo+1)%h)<dot(lo):lo=(lo+1)%h
  while normal((far+1)%h)<normal(far):far=(far+1)%h
 numerator=(dot(hi)-dot(lo))*(normal(i)-normal(far));denominator=dx*dx+dy*dy
 if best_num is None or numerator*best_den<best_num*denominator:best_num=numerator;best_den=denominator
getcontext().prec=50;print(f'{Decimal(best_num)/Decimal(best_den):.10f}')
