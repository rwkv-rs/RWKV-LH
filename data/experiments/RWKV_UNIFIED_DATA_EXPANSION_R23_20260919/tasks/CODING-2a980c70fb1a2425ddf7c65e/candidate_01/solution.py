import sys,itertools
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];tasks=sorted(zip(v[1:n+1],v[n+1:]),reverse=True);groups=[]
for power,rows in itertools.groupby(tasks,key=lambda x:x[0]):groups.append((power,sorted((b for a,b in rows),reverse=True)))
def possible(threshold):
 dp=[0]+[10**30]*n;processed=0
 for power,bs in groups:
  g=len(bs);prefix=[0]
  for b in bs:prefix.append(prefix[-1]+1000*power-threshold*b)
  new=[10**30]*(n+1)
  for old in range(processed+1):
   if dp[old]==10**30:continue
   for selected in range(max(0,g-old),g+1):
    remaining=old-g+2*selected;new[remaining]=min(new[remaining],dp[old]+prefix[selected])
  dp=new;processed+=g
 return min(dp)<=0
lo=0;hi=max((1000*a+b-1)//b for a,b in tasks)
while lo<hi:
 mid=(lo+hi)//2
 if possible(mid):hi=mid
 else:lo=mid+1
print(lo)
