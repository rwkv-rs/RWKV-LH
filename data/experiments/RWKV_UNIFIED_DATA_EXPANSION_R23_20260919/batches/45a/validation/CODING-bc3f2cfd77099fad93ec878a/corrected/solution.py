import sys,bisect
v=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(v),next(v);adj=[[] for _ in range(n)]
for _ in range(m):a,b=next(v)-1,next(v)-1;adj[a].append(b);adj[b].append(a)
tin=[-1]*n;tout=[0]*n;low=[0]*n;parent=[-1]*n;children=[[] for _ in range(n)];timer=1;tin[0]=low[0]=0;stack=[(0,0)]
while stack:
 x,j=stack[-1]
 if j==len(adj[x]):
  stack.pop();tout[x]=timer
  if parent[x]>=0:low[parent[x]]=min(low[parent[x]],low[x])
  continue
 y=adj[x][j];stack[-1]=(x,j+1)
 if y==parent[x]:continue
 if tin[y]<0:parent[y]=x;children[x].append(y);tin[y]=low[y]=timer;timer+=1;stack.append((y,0))
 else:low[x]=min(low[x],tin[y])
starts=[[tin[y] for y in part] for part in children]
def component(x,removed):
 if not (tin[removed]<tin[x]<tout[removed]):return -1
 child=children[removed][bisect.bisect_right(starts[removed],tin[x])-1]
 return child if low[child]>=tin[removed] else -1
out=[]
for _ in range(next(v)):
 s,t,m=next(v)-1,next(v)-1,next(v)-1;out.append('yes' if component(s,m)!=component(t,m) else 'no')
print('\n'.join(out))
