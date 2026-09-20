import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];initial=[tuple(v[i:i+2]) for i in range(1,1+2*n,2)];q=v[1+2*n];operations=[tuple(v[i:i+3]) for i in range(2+2*n,len(v),3)];points=initial+[(x,y) for op,x,y in operations if op==0];points=list(set(points));nodes=[];leaf={}
def build(ps,parent=-1,axis=0):
 u=len(nodes);nodes.append(None)
 if len(ps)==1:
  x,y=ps[0];nodes[u]=[-1,-1,parent,x,x,y,y,0];leaf[x,y]=u;return u
 ps.sort(key=lambda p:p[axis]);mid=len(ps)//2;l=build(ps[:mid],u,axis^1);r=build(ps[mid:],u,axis^1);a=nodes[l];b=nodes[r];nodes[u]=[l,r,parent,min(a[3],b[3]),max(a[4],b[4]),min(a[5],b[5]),max(a[6],b[6]),0];return u
build(points);minsum=mindiff=10**30;maxsum=maxdiff=-10**30
def insert(x,y):
 global minsum,mindiff,maxsum,maxdiff
 u=leaf[x,y]
 if nodes[u][7]:return
 while u>=0:nodes[u][7]+=1;u=nodes[u][2]
 minsum=min(minsum,x+y);maxsum=max(maxsum,x+y);mindiff=min(mindiff,x-y);maxdiff=max(maxdiff,x-y)
def lower(u,x,y):
 node=nodes[u]
 if not node[7]:return 10**30
 return max(node[3]-x,0,x-node[4])+max(node[5]-y,0,y-node[6])
def nearest(x,y):
 best=10**30;stack=[(0,0)]
 while stack:
  bound,u=stack.pop()
  if bound>=best:continue
  node=nodes[u]
  if node[0]<0:
   if node[7]:best=abs(x-node[3])+abs(y-node[5])
   continue
  l,r=node[:2];dl=lower(l,x,y);dr=lower(r,x,y)
  if dl<dr:
   if dr<best:stack.append((dr,r))
   if dl<best:stack.append((dl,l))
  else:
   if dl<best:stack.append((dl,l))
   if dr<best:stack.append((dr,r))
 return best
for x,y in initial:insert(x,y)
out=[]
for op,x,y in operations:
 if op==0:insert(x,y)
 elif op==1:out.append(str(nearest(x,y)))
 else:out.append(str(max(x+y-minsum,maxsum-x-y,x-y-mindiff,maxdiff-x+y)))
print('\n'.join(out))
