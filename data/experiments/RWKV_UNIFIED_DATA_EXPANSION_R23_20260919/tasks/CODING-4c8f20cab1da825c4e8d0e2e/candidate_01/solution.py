import sys,itertools
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);edges=[]
for _ in range(m):
 a,b,w=next(v)-1,next(v)-1,next(v);edges.append((w,a,b))
edges.sort();parent=list(range(n))
def find(p,x):
 while p[x]!=x:p[x]=p[p[x]];x=p[x]
 return x
answer=1
for weight,group in itertools.groupby(edges,key=lambda x:x[0]):
 pairs=[(find(parent,a),find(parent,b)) for _,a,b in group];pairs=[(a,b) for a,b in pairs if a!=b];roots=sorted({x for ab in pairs for x in ab});lookup={x:i for i,x in enumerate(roots)};pairs=[(lookup[a],lookup[b]) for a,b in pairs];base=list(range(len(roots)));rank=0
 for a,b in pairs:
  a=find(base,a);b=find(base,b)
  if a!=b:base[a]=b;rank+=1
 ways=0
 for chosen in itertools.combinations(pairs,rank):
  p=list(range(len(roots)));ok=True
  for a,b in chosen:
   a=find(p,a);b=find(p,b)
   if a==b:ok=False;break
   p[a]=b
  ways+=ok
 answer=answer*ways%31011
 for a,b in pairs:
  a=find(parent,roots[a]);b=find(parent,roots[b])
  if a!=b:parent[a]=b
print(answer if len({find(parent,i) for i in range(n)})==1 else 0)
