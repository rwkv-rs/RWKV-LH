import sys,bisect
v=sys.stdin.buffer.read().split();n,m=int(v[0]),int(v[1]);s=v[2].decode();bit=[0]+[i&-i for i in range(1,n+1)];positions={}
for i,c in enumerate(s):positions.setdefault(c,[]).append(i)
parents={c:list(range(len(p)+1)) for c,p in positions.items()};alive=bytearray(b'\1')*n
power=1<<(n.bit_length()-1)
def kth(k):
 p=0;step=power
 while step:
  q=p+step
  if q<=n and bit[q]<k:k-=bit[q];p=q
  step>>=1
 return p
def find(parent,i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for i in range(3,len(v),3):
 l,r=int(v[i]),int(v[i+1]);c=v[i+2].decode()
 if c not in positions:continue
 L,R=kth(l),kth(r);p=positions[c];parent=parents[c];j=find(parent,bisect.bisect_left(p,L))
 while j<len(p) and p[j]<=R:
  x=p[j];alive[x]=0;u=x+1
  while u<=n:bit[u]-=1;u+=u&-u
  parent[j]=find(parent,j+1);j=parent[j]
print(''.join(c for i,c in enumerate(s) if alive[i]))
