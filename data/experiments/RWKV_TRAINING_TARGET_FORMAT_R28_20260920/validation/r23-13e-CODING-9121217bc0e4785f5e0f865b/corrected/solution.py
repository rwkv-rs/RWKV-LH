import sys
v=sys.stdin.buffer.read().split();cases=int(v[0]);at=1;out=[]
for _ in range(cases):
 n=int(v[at]);at+=1;parent=list(range(n+1));distance=[0]*(n+1)
 while True:
  kind=v[at];at+=1
  if kind in (b'O',b'0'):break
  u=int(v[at]);at+=1
  if kind==b'I':
   p=int(v[at]);at+=1;parent[u]=p;distance[u]=abs(u-p)%1000
  else:
   path=[];x=u
   while parent[x]!=x:path.append(x);x=parent[x]
   total=0
   for y in reversed(path):total+=distance[y];distance[y]=total;parent[y]=x
   out.append(str(distance[u]))
print('\n'.join(out))
