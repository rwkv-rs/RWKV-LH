import sys
v=iter(map(int,sys.stdin.buffer.read().split()));n,K=next(v),next(v);values=[next(v) for _ in range(n)];weights=[next(v) for _ in range(n)];g=[[] for _ in range(n)]
for _ in range(n-1):a,b=next(v)-1,next(v)-1;g[a].append(b);g[b].append(a)
parent=[-1]*n;order=[0]
for u in order:
 for z in g[u]:
  if z!=parent[u]:parent[z]=u;order.append(z)
def feasible(ratio):
 dp=[None]*n
 for u in reversed(order):
  row=[-1e100,values[u]-ratio*weights[u]]
  for z in g[u]:
   if parent[z]!=u:continue
   other=dp[z];new=row+[-1e100]*(len(other)-1)
   for a in range(1,len(row)):
    for b in range(1,len(other)):new[a+b]=max(new[a+b],row[a]+other[b])
   row=new
  if len(row)>K and max(row[K:])>=0:return True
  dp[u]=row
 return False
lo=0.0;hi=max(x/w for x,w in zip(values,weights))
for _ in range(55):
 mid=(lo+hi)/2
 if feasible(mid):lo=mid
 else:hi=mid
print(f'{lo:.2f}')
