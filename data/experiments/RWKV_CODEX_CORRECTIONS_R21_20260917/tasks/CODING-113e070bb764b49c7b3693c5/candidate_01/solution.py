import sys
it=iter(sys.stdin.buffer.read().split());out=[]
while True:
 try:n=int(next(it))
 except StopIteration:break
 if not n:break
 p=[(float(next(it)),float(next(it))) for _ in range(n)];points=[(x,y-d) for x,y in p for d in (0,1)];best=p[0][0];through=False
 for i,(x,y) in enumerate(points):
  if through:break
  for u,v in points[i+1:]:
   if abs(u-x)<1e-12:continue
   slope=(v-y)/(u-x);intercept=y-slope*x;first=slope*p[0][0]+intercept
   if first<p[0][1]-1-1e-8 or first>p[0][1]+1e-8:continue
   reached=p[-1][0]
   for j in range(1,n):
    xx,upper=p[j];ray=slope*xx+intercept
    if ray<upper-1-1e-8 or ray>upper+1e-8:
     shift=0 if ray>upper else -1;px,py=p[j-1];before=slope*px+intercept-(py+shift);after=ray-(upper+shift);reached=px+(xx-px)*(-before)/(after-before);break
   else:through=True
   best=max(best,reached)
   if through:break
 out.append('Through all the pipe.' if through else f'{best:.2f}')
print('\n'.join(out))
