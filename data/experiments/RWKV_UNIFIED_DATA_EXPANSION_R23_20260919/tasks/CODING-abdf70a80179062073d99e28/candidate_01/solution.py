import sys,math
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];b=v[n+1:2*n+1];c=v[2*n+1:];bound=math.isqrt(max(a));sieve=bytearray(b'\1')*(bound+1);primes=[]
for i in range(2,bound+1):
 if sieve[i]:
  primes.append(i)
  if i*i<=bound:sieve[i*i:bound+1:i]=b'\0'*((bound-i*i)//i+1)
factors=[];parity=[];where={}
for i,value in enumerate(a):
 where.setdefault(value,[]).append(i);x=value;divisors=[];count=0
 for p in primes:
  if p*p>x:break
  if x%p==0:
   divisors.append(p)
   while x%p==0:x//=p;count+=1
 if x>1:divisors.append(x);count+=1
 factors.append(divisors);parity.append(count%2)
source=n;sink=n+1;graph=[[] for _ in range(n+2)]
def add(u,v,cap,cost):
 forward=[v,len(graph[v]),cap,cost];backward=[u,len(graph[u]),0,-cost];graph[u].append(forward);graph[v].append(backward)
for i in range(n):
 if parity[i]==0:add(source,i,b[i],0)
 else:add(i,sink,b[i],0)
for i in range(n):
 for prime in factors[i]:
  for j in where.get(a[i]//prime,[]):
   u,w=(i,j) if parity[i]==0 else (j,i);add(u,w,min(b[i],b[j]),-c[i]*c[j])
flow=0;cost=0;inf=10**40
while True:
 dist=[inf]*(n+2);dist[source]=0;previous=[None]*(n+2);queue=deque([source]);queued=[False]*(n+2);queued[source]=True
 while queue:
  u=queue.popleft();queued[u]=False
  for index,e in enumerate(graph[u]):
   w,rev,cap,weight=e
   if cap and dist[w]>dist[u]+weight:
    dist[w]=dist[u]+weight;previous[w]=(u,index)
    if not queued[w]:queue.append(w);queued[w]=True
 if dist[sink]==inf:break
 amount=10**30;u=sink
 while u!=source:
  p,index=previous[u];amount=min(amount,graph[p][index][2]);u=p
 if dist[sink]>0:amount=min(amount,(-cost)//dist[sink])
 if amount==0:break
 u=sink
 while u!=source:
  p,index=previous[u];e=graph[p][index];e[2]-=amount;graph[u][e[1]][2]+=amount;u=p
 flow+=amount;cost+=amount*dist[sink]
print(flow)
