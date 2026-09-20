import sys
v=sys.stdin.buffer.read().split();n,k=map(int,v[:2]);text=v[2]+b'{'+v[3];N=len(text);sa=list(range(N));rank=list(text);step=1
while step<N:
 sa.sort(key=lambda i:(rank[i],rank[i+step] if i+step<N else -1));new=[0]*N
 for j in range(1,N):
  a,b=sa[j-1],sa[j];new[b]=new[a]+int((rank[a],rank[a+step] if a+step<N else -1)!=(rank[b],rank[b+step] if b+step<N else -1))
 rank=new
 if rank[sa[-1]]==N-1:break
 step*=2
lcp=[0]*N;length=0
for i in range(N):
 order=rank[i]
 if not order:continue
 j=sa[order-1]
 while i+length<N and j+length<N and text[i+length]==text[j+length]:length+=1
 lcp[order]=min(k,length)
 if length:length-=1
parent=list(range(N));size=[1]*N;balance=[int(i<=n-k)-int(n+1<=i<=2*n+1-k) for i in sa]
def find(u):
 while parent[u]!=u:parent[u]=parent[parent[u]];u=parent[u]
 return u
saving=0
for edge in sorted(range(1,N),key=lambda i:lcp[i],reverse=True):
 a,b=find(edge-1),find(edge)
 if balance[a]*balance[b]<0:saving+=min(abs(balance[a]),abs(balance[b]))*lcp[edge]
 if size[a]<size[b]:a,b=b,a
 parent[b]=a;size[a]+=size[b];balance[a]+=balance[b]
print(k*(n-k+1)-saving)
