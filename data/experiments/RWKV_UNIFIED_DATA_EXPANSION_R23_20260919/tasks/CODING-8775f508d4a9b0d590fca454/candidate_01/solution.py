import sys
MOD=1000000007;lines=sys.stdin.buffer;N,M=map(int,lines.readline().split());children=[[] for _ in range(N)];parent=[0]*N
for i in range(1,N):parent[i]=int(lines.readline())-1;children[parent[i]].append(i)
depth=[0]*N;order=[0]
for u in order:
 for w in children[u]:depth[w]=depth[u]+1;order.append(w)
size=[1]*N;heavy=[-1]*N
for u in reversed(order):
 for w in children[u]:
  size[u]+=size[w]
  if heavy[u]<0 or size[w]>size[heavy[u]]:heavy[u]=w
pos=[0]*N;head=[0]*N;sequence=[];stack=[(0,0)]
while stack:
 u,h=stack.pop()
 while u>=0:
  head[u]=h;pos[u]=len(sequence);sequence.append(u)
  for w in children[u]:
   if w!=heavy[u]:stack.append((w,w))
  u=heavy[u]
f=[0,1]
for i in range(N+2):f.append((f[-1]+f[-2])%MOD)
basis0=[0];basis1=[0]
for u in sequence:basis0.append((basis0[-1]+f[depth[u]])%MOD);basis1.append((basis1[-1]+f[depth[u]+1])%MOD)
tree=[0]*(4*N);lazy0=[0]*(4*N);lazy1=[0]*(4*N)
def apply(p,l,r,a,b):tree[p]=(tree[p]+a*(basis0[r+1]-basis0[l])+b*(basis1[r+1]-basis1[l]))%MOD;lazy0[p]=(lazy0[p]+a)%MOD;lazy1[p]=(lazy1[p]+b)%MOD
def push(p,l,r):
 if l<r and (lazy0[p] or lazy1[p]):
  mid=(l+r)//2;apply(p*2,l,mid,lazy0[p],lazy1[p]);apply(p*2+1,mid+1,r,lazy0[p],lazy1[p]);lazy0[p]=lazy1[p]=0
def update(p,l,r,ql,qr,a,b):
 if ql<=l and r<=qr:apply(p,l,r,a,b);return
 push(p,l,r);mid=(l+r)//2
 if ql<=mid:update(p*2,l,mid,ql,qr,a,b)
 if qr>mid:update(p*2+1,mid+1,r,ql,qr,a,b)
 tree[p]=(tree[p*2]+tree[p*2+1])%MOD
def query(p,l,r,ql,qr):
 if ql<=l and r<=qr:return tree[p]
 push(p,l,r);mid=(l+r)//2;answer=0
 if ql<=mid:answer+=query(p*2,l,mid,ql,qr)
 if qr>mid:answer+=query(p*2+1,mid+1,r,ql,qr)
 return answer%MOD
def fibonacci(k):
 negative=k<0;k=abs(k);a,b=0,1
 for bit in bin(k)[2:]:
  c=a*(2*b-a)%MOD;d=(a*a+b*b)%MOD;a,b=(c,d) if bit=='0' else (d,(c+d)%MOD)
 return -a%MOD if negative and k%2==0 else a
out=[]
for _ in range(M):
 op,x,y=lines.readline().split();x=int(x)-1;y=int(y)
 if op==b'U':
  shift=y-depth[x];update(1,0,N-1,pos[x],pos[x]+size[x]-1,fibonacci(shift-1),fibonacci(shift))
 else:
  y-=1;answer=0
  while head[x]!=head[y]:
   if depth[head[x]]<depth[head[y]]:x,y=y,x
   answer+=query(1,0,N-1,pos[head[x]],pos[x]);x=parent[head[x]]
  if depth[x]>depth[y]:x,y=y,x
  answer+=query(1,0,N-1,pos[x],pos[y]);out.append(str(answer%MOD))
print('\n'.join(out))
