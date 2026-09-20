import sys
sys.set_int_max_str_digits(0)
stream=sys.stdin.buffer;n,m=map(int,stream.readline().split());adj=[[] for _ in range(n)];edges=0
for _ in range(m):
 row=list(map(int,stream.readline().split()));vertices=row[1:]
 for a,b in zip(vertices,vertices[1:]):
  a-=1;b-=1;adj[a].append((b,edges));adj[b].append((a,edges));edges+=1
entered=[-1]*n;parent=[-1]*n;parent_edge=[-1]*n;used=bytearray(edges);seen_edge=bytearray(edges);entered[0]=0;order=1;stack=[(0,0)];answer=1;valid=True
while stack and valid:
 u,index=stack[-1]
 if index==len(adj[u]):stack.pop();continue
 stack[-1]=(u,index+1);v,e=adj[u][index]
 if seen_edge[e]:continue
 seen_edge[e]=1
 if entered[v]<0:
  entered[v]=order;order+=1;parent[v]=u;parent_edge[v]=e;stack.append((v,0))
 else:
  # In an undirected depth-first traversal every unused non-tree edge closes an ancestor cycle.
  length=1;x=u
  while x!=v:
   pe=parent_edge[x]
   if pe<0 or used[pe]:valid=False;break
   used[pe]=1;length+=1;x=parent[x]
  if valid:answer*=length+1
print(answer if valid and order==n else 0)
