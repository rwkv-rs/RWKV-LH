import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=1;out=[]
for _ in range(v[0]):
 n,q=v[p:p+2];p+=2;subnets=[]
 for j in range(q):
  count,cost=v[p:p+2];p+=2;nodes=[x-1 for x in v[p:p+count]];p+=count;subnets.append((cost,nodes))
 points=[tuple(v[p+2*i:p+2*i+2]) for i in range(n)];p+=2*n;distance=[10**30]*n;distance[0]=0;parent=[-1]*n;used=[False]*n;tree=[]
 for step in range(n):
  u=-1;best=10**30
  for i in range(n):
   if not used[i] and distance[i]<best:best=distance[i];u=i
  used[u]=True
  if parent[u]>=0:tree.append((best,u,parent[u]))
  x,y=points[u]
  for i,(xx,yy) in enumerate(points):
   if not used[i]:
    value=(x-xx)**2+(y-yy)**2
    if value<distance[i]:distance[i]=value;parent[i]=u
 tree.sort();answer=sum(w for w,a,b in tree)
 for mask in range(1,1<<q):
  parent=list(range(n));sizes=[1]*n;cost=0
  def find(u):
   while parent[u]!=u:parent[u]=parent[parent[u]];u=parent[u]
   return u
  def union(a,b):
   a=find(a);b=find(b)
   if a==b:return False
   if sizes[a]<sizes[b]:a,b=b,a
   parent[b]=a;sizes[a]+=sizes[b];return True
  for j,(price,nodes) in enumerate(subnets):
   if mask>>j&1:
    cost+=price
    for node in nodes[1:]:union(nodes[0],node)
  for weight,a,b in tree:
   if union(a,b):cost+=weight
  answer=min(answer,cost)
 out.append(str(answer))
print('\n\n'.join(out))
