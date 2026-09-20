import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);parents=[0]*(n+1);depth=[0]*(n+1);zeros=list(range(n+1));ones=list(range(n+1));roots=[0]*(n+1)
for i in range(1,n+1):
 p=next(it);kind=next(it)
 if p==-1:roots[i]=i;continue
 parents[i]=p;depth[i]=depth[p]+1;roots[i]=roots[p]
 if kind==0:zeros[i]=zeros[p]
 else:ones[i]=ones[p]
up=[parents]
for k in range(1,n.bit_length()):
 last=up[-1];up.append([last[last[i]] for i in range(n+1)])
def lca(a,b):
 if depth[a]<depth[b]:a,b=b,a
 difference=depth[a]-depth[b]
 while difference:
  bit=difference&-difference;a=up[bit.bit_length()-1][a];difference-=bit
 if a==b:return a
 for level in reversed(up):
  if level[a]!=level[b]:a=level[a];b=level[b]
 return parents[a]
out=[]
for _ in range(next(it)):
 kind=next(it);u=next(it);v=next(it);ok=False
 if u!=v and roots[u]==roots[v]:
  ancestor=lca(u,v)
  if kind==1:ok=ancestor==u and zeros[u]==zeros[v]
  else:ok=ancestor!=v and zeros[u]==zeros[ancestor] and ones[v]==ones[ancestor]
 out.append('YES' if ok else 'NO')
print('\n'.join(out))
