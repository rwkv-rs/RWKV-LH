import sys
v=iter(sys.stdin.buffer.read().split());n=int(next(v));q=int(next(v));parent=list(range(n+1));count=[0]*(n+1);count[1]=1
for _ in range(n-1):a=int(next(v));b=int(next(v));parent[b]=a
ops=[]
for _ in range(q):
 op=next(v);x=int(next(v));ops.append((op,x))
 if op==b'C':count[x]+=1
dsu=[i if count[i] else parent[i] for i in range(n+1)]
def find(x):
 root=x
 while dsu[root]!=root:root=dsu[root]
 while dsu[x]!=x:y=dsu[x];dsu[x]=root;x=y
 return root
out=[]
for op,x in reversed(ops):
 if op==b'Q':out.append(str(find(x)))
 else:
  count[x]-=1
  if count[x]==0:dsu[x]=find(parent[x])
print('\n'.join(reversed(out)))
