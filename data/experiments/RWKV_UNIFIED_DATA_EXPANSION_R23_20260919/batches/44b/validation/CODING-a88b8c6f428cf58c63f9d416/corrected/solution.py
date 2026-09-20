import sys
v=list(map(int,sys.stdin.buffer.read().split()));edges=[]
for i in range(0,len(v),3):
 u,w,ident=v[i:i+3]
 if u==0 and w==0:break
 edges.append((u,w,ident))
adj={}
for i,(u,w,ident) in enumerate(edges):adj.setdefault(u,[]).append((ident,w,i));adj.setdefault(w,[]).append((ident,u,i))
if not edges or any(len(a)%2 for a in adj.values()):print('Round trip does not exist')
else:
 for a in adj.values():a.sort(reverse=True)
 u,w,_=min(edges,key=lambda e:e[2]);start=min(u,w);stack=[(start,None)];used=[False]*len(edges);answer=[]
 while stack:
  u,incoming=stack[-1]
  while adj[u] and used[adj[u][-1][2]]:adj[u].pop()
  if not adj[u]:
   stack.pop()
   if incoming is not None:answer.append(incoming)
  else:
   ident,w,i=adj[u].pop();used[i]=True;stack.append((w,ident))
 if len(answer)!=len(edges):print('Round trip does not exist')
 else:print(' '.join(map(str,reversed(answer))))
