import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);m=next(v);g=[[] for i in range(n)];reverse=[[] for i in range(n)];edges=[]
 for i in range(m):
  a=next(v)-1;b=next(v)-1;g[a].append(b);reverse[b].append(a);edges.append((a,b))
 seen=[False]*n;order=[]
 for root in range(n):
  if seen[root]:continue
  stack=[(root,0)];seen[root]=True
  while stack:
   a,pos=stack[-1]
   if pos==len(g[a]):order.append(a);stack.pop();continue
   b=g[a][pos];stack[-1]=(a,pos+1)
   if not seen[b]:seen[b]=True;stack.append((b,0))
 comp=[-1]*n;count=0
 for root in reversed(order):
  if comp[root]>=0:continue
  comp[root]=count;stack=[root]
  while stack:
   a=stack.pop()
   for b in reverse[a]:
    if comp[b]<0:comp[b]=count;stack.append(b)
  count+=1
 incoming=[False]*count;outgoing=[False]*count
 for a,b in edges:
  if comp[a]!=comp[b]:outgoing[comp[a]]=True;incoming[comp[b]]=True
 out.append(str(0 if count==1 else max(incoming.count(False),outgoing.count(False))))
print('\n'.join(out))
