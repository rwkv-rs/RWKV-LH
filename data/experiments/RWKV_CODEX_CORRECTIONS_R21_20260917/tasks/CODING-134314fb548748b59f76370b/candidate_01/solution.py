import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);m=next(it);g=[[] for _ in range(n)];rev=[[] for _ in range(n)];edges=[]
 for _ in range(m):
  a=next(it)-1;b=next(it)-1;g[a].append(b);rev[b].append(a);edges.append((a,b))
 seen=bytearray(n);order=[]
 for root in range(n):
  if seen[root]:continue
  seen[root]=1;stack=[(root,0)]
  while stack:
   x,i=stack[-1]
   if i<len(g[x]):
    y=g[x][i];stack[-1]=(x,i+1)
    if not seen[y]:seen[y]=1;stack.append((y,0))
   else:order.append(x);stack.pop()
 comp=[-1]*n;count=0
 for root in reversed(order):
  if comp[root]>=0:continue
  comp[root]=count;stack=[root]
  while stack:
   x=stack.pop()
   for y in rev[x]:
    if comp[y]<0:comp[y]=count;stack.append(y)
  count+=1
 incoming=[0]*count;outgoing=[0]*count
 for a,b in edges:
  if comp[a]!=comp[b]:outgoing[comp[a]]=1;incoming[comp[b]]=1
 out.append(str(0 if count==1 else max(incoming.count(0),outgoing.count(0))))
print('\n'.join(out))
