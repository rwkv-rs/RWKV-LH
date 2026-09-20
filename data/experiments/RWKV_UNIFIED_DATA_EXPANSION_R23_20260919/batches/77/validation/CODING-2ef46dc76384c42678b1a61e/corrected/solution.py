import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];parent=list(range(n));kind=[0]*n;depth=[0]*n;ones=[0]*n;roots=list(range(n));p=1
for i in range(n):
 a,t=v[p:p+2];p+=2
 if a!=-1:parent[i]=a-1;kind[i]=t;depth[i]=depth[a-1]+1;ones[i]=ones[a-1]+t;roots[i]=roots[a-1]
size=[1]*n;heavy=[-1]*n
for i in range(n-1,-1,-1):
 a=parent[i]
 if a!=i:
  size[a]+=size[i]
  if heavy[a]<0 or size[i]>size[heavy[a]]:heavy[a]=i
head=list(range(n))
for i in range(n):
 if parent[i]!=i and heavy[parent[i]]==i:head[i]=head[parent[i]]
def lca(a,b):
 while head[a]!=head[b]:
  if depth[head[a]]>depth[head[b]]:a=parent[head[a]]
  else:b=parent[head[b]]
 return a if depth[a]<depth[b] else b
q=v[p];p+=1;out=[]
for _ in range(q):
 t,u,w=v[p:p+3];p+=3;u-=1;w-=1
 if u==w or roots[u]!=roots[w]:out.append('NO');continue
 ancestor=lca(u,w)
 if t==1:ok=ancestor==u and ones[w]==ones[u]
 else:ok=ancestor!=w and ones[u]==ones[ancestor] and ones[w]-ones[ancestor]==depth[w]-depth[ancestor]
 out.append('YES' if ok else 'NO')
print('\n'.join(out))
