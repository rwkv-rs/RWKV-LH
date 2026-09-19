import sys,math
v=iter(map(int,sys.stdin.read().split()));out=[];case=0
for n in v:
 if n==0:break
 a=[(next(v)*60,next(v)*60) for _ in range(n)];size=1<<n
 def possible(gap):
  best=[float('inf')]*size;best[0]=-gap
  for mask in range(size):
   if best[mask]==float('inf'):continue
   for i,(l,r) in enumerate(a):
    if mask>>i&1:continue
    time=max(l,best[mask]+gap)
    if time<=r:best[mask|1<<i]=min(best[mask|1<<i],time)
  return best[-1]<float('inf')
 lo=0.;hi=86401.
 for _ in range(55):
  mid=(lo+hi)/2
  if possible(mid):lo=mid
  else:hi=mid
 seconds=int(math.floor(lo+0.50000001));case+=1;out.append(f'Case {case}: {seconds//60}:{seconds%60:02d}')
print('\n'.join(out))
