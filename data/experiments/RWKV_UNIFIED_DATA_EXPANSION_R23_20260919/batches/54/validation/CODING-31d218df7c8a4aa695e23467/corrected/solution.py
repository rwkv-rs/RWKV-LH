import sys,math
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];values=v[1:];maximum=max(values);spf=array('i',range(maximum+1))
for p in range(2,math.isqrt(maximum)+1):
 if spf[p]==p:
  for j in range(p*p,maximum+1,p):
   if spf[j]==j:spf[j]=p
groups={}
for literal,x in enumerate(values):
 while x>1:
  p=spf[x];groups.setdefault(p,[]).append(literal)
  while x%p==0:x//=p
g=[[] for _ in range(2*n)]
def clause(a,b):g[a^1].append(b);g[b^1].append(a)
for literals in groups.values():
 if len(literals)<2:continue
 previous=None
 for i,lit in enumerate(literals):
  if i==len(literals)-1:clause(lit^1,previous^1);break
  current=len(g);g.extend([[],[]]);clause(lit^1,current)
  if previous is not None:clause(previous^1,current);clause(lit^1,previous^1)
  previous=current
N=len(g);index=[-1]*N;low=[0]*N;component=[-1]*N;active=bytearray(N);nodes=[];timer=0;cid=0
for root in range(N):
 if index[root]>=0:continue
 index[root]=low[root]=timer;timer+=1;nodes.append(root);active[root]=1;stack=[(root,0)]
 while stack:
  u,j=stack[-1]
  if j<len(g[u]):
   z=g[u][j];stack[-1]=(u,j+1)
   if index[z]<0:index[z]=low[z]=timer;timer+=1;nodes.append(z);active[z]=1;stack.append((z,0))
   elif active[z]:low[u]=min(low[u],index[z])
  else:
   stack.pop()
   if stack:parent=stack[-1][0];low[parent]=min(low[parent],low[u])
   if low[u]==index[u]:
    while True:
     z=nodes.pop();active[z]=0;component[z]=cid
     if z==u:break
    cid+=1
print('Yes' if all(component[i]!=component[i^1] for i in range(0,N,2)) else 'No')
