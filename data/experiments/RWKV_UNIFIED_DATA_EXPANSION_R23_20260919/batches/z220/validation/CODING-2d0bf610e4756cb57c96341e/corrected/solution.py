import sys,math
def solve(s,n,t,day,zone,p,m):
 period=10080;days={'Sun':0,'Mon':1,'Tue':2,'Wed':3,'Thu':4,'Fri':5,'Sat':6};allowed=[]
 for minute in range(period):
  clock=minute%1440;ok_day=day=='All' or minute//1440==days[day];ok_time=zone=='All' or (360<=clock<1080 if zone=='Day' else clock<360 or clock>=1080);allowed.append(ok_day and ok_time)
 prefix=[0]
 for yes in allowed+allowed:prefix.append(prefix[-1]+int(not yes))
 valid=[int(prefix[start+s+1]==prefix[start]) for start in range(period)];best=0;g=math.gcd(t,period)
 for root in range(g):
  cycle=[];x=root
  while True:
   cycle.append(valid[x]);x=(x+t)%period
   if x==root:break
  length=len(cycle);whole,remainder=divmod(m,length);base=whole*sum(cycle);window=sum(cycle[:remainder]);best=max(best,base+window)
  if remainder:
   for i in range(length-1):window+=cycle[(i+remainder)%length]-cycle[i];best=max(best,base+window)
 trials=n*best
 if not trials:return 0.
 if p==1:return 1.
 return -math.expm1(trials*math.log1p(-1./p))
out=[]
for line in sys.stdin:
 v=line.split()
 if not v:continue
 s,n,t=map(int,v[:3]);p,m=map(int,v[5:])
 if s==0:break
 out.append(f'{solve(s,n,t,v[3],v[4],p,m):.12f}')
print('\n'.join(out))
