import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];c=v[1:n+1];g=[[] for _ in range(n)]
for i in range(n+1,len(v),2):
 a,b=v[i]-1,v[i+1]-1;g[a].append(b);g[b].append(a)
par=[-1]*n;order=[0]
for x in order:
 for y in g[x]:
  if y!=par[x]:par[y]=x;order.append(y)
d=[None]*n;freq=[0]*n;ans=[0]*n
for x in reversed(order):
 children=[y for y in g[x] if par[y]==x];heavy=max(children,key=lambda y:len(d[y])) if children else -1
 if heavy<0:base={};best=0;total=0
 else:base=d[heavy];best=freq[heavy];total=ans[heavy];d[heavy]=None
 for y in children:
  if y==heavy:continue
  for col,num in d[y].items():
   count=base.get(col,0)+num;base[col]=count
   if count>best:best=count;total=col
   elif count==best:total+=col
  d[y]=None
 col=c[x];count=base.get(col,0)+1;base[col]=count
 if count>best:best=count;total=col
 elif count==best:total+=col
 d[x]=base;freq[x]=best;ans[x]=total
print(*ans)
