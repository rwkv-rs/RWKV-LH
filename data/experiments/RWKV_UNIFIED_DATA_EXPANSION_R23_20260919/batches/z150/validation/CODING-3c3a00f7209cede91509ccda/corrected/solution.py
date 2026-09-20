import sys
v=iter(map(int,sys.stdin.buffer.read().split()));tests=next(v);out=[]
for _ in range(tests):
 n=next(v);m=next(v);cats=[]
 for i in range(n):
  a=next(v);b=next(v);s=next(v);velocity=(b>a)-(b<a);cats.append((velocity,a-velocity*s,2*s,2*(s+abs(a-b))))
 for _ in range(m):
  c=next(v);d=next(v);r=next(v);velocity=(d>c)-(d<c);intercept=c-velocity*r;start=2*r;end=2*(r+abs(c-d));best=10**30;who=-1
  for i,(speed,offset,begin,finish) in enumerate(cats,1):
   lower=max(start,begin);upper=min(end,finish)
   if lower>upper or lower>=best:continue
   difference=speed-velocity
   if difference:
    numerator=2*(intercept-offset)
    if numerator%difference:continue
    meet=numerator//difference
    if meet<lower or meet>upper:continue
   elif intercept==offset:meet=lower
   else:continue
   if meet<best:best=meet;who=i
  out.append(str(who))
print('\n'.join(out))
