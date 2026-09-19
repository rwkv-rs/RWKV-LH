import sys
v=list(map(int,sys.stdin.buffer.read().split()));at=0;out=[];inf=10**9
while at<len(v):
 n=v[at];at+=1
 if n<=0:break
 g=[[] for _ in range(n)]
 for _ in range(n-1):
  a,b=v[at]-1,v[at+1]-1;at+=2;g[a].append(b);g[b].append(a)
 parent=[-1]*n;order=[0];parent[0]=0
 for x in order:
  for y in g[x]:
   if y!=parent[x]:parent[y]=x;order.append(y)
 server=[0]*n;child_cover=[0]*n;parent_cover=[0]*n
 for x in reversed(order):
  children=[y for y in g[x] if parent[y]==x];server[x]=1+sum(min(server[y],parent_cover[y]) for y in children);base=sum(child_cover[y] for y in children);parent_cover[x]=base;child_cover[x]=min((base-child_cover[y]+server[y] for y in children),default=inf)
 out.append(str(min(server[0],child_cover[0])))
 if at<len(v):
  separator=v[at];at+=1
  if separator==-1:break
print('\n'.join(out))
