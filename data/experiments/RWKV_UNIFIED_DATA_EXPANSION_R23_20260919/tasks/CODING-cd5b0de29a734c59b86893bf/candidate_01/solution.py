import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));queries=[v[i:i+3] for i in range(1,len(v),3)];limit=max((p for x,p,k in queries),default=1);spf=list(range(limit+1))
for i in range(2,math.isqrt(limit)+1):
 if spf[i]==i:
  for j in range(i*i,limit+1,i):
   if spf[j]==j:spf[j]=i
cache={};out=[]
for x,p,k in queries:
 if p not in cache:
  factors=[];q=p
  while q>1:
   f=spf[q];factors.append(f)
   while q%f==0:q//=f
  terms=[(1,1)]
  for f in factors:terms += [(d*f,-s) for d,s in terms[:]]
  cache[p]=terms
 terms=cache[p]
 def count(t):return sum(s*(t//d) for d,s in terms)
 target=count(x)+k;lo=x+1;hi=x+max(1,k)
 while count(hi)<target:hi=x+2*(hi-x)
 while lo<hi:
  mid=(lo+hi)//2
  if count(mid)>=target:hi=mid
  else:lo=mid+1
 out.append(str(lo))
print('\n'.join(out))
