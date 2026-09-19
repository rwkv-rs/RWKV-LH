import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
while True:
 try:n=next(it)
 except StopIteration:break
 if not n:break
 d=[[next(it) for _ in range(n)] for _ in range(n)];g={i:{} for i in range(n)};nextid=n
 def edge(a,b,w):g[a][b]=w;g[b][a]=w
 def build(count):
  global nextid
  if count==2:edge(0,1,d[0][1]);return
  if count<2:return
  leaf=count-1;limb=min((d[i][leaf]+d[j][leaf]-d[i][j])//2 for i in range(leaf) for j in range(i+1,leaf))
  pair=next((i,j) for i in range(leaf) for j in range(i+1,leaf) if d[i][leaf]+d[j][leaf]-2*limb==d[i][j]);start,end=pair;distance=d[start][leaf]-limb;build(leaf);parents={start:None};stack=[start]
  for x in stack:
   if x==end:break
   for y in g[x]:
    if y not in parents:parents[y]=x;stack.append(y)
  path=[end]
  while path[-1]!=start:path.append(parents[path[-1]])
  path.reverse();attach=start
  for a,b in zip(path,path[1:]):
   if distance==0:attach=a;break
   w=g[a][b]
   if distance<w:
    attach=nextid;nextid+=1;g[attach]={};del g[a][b];del g[b][a];edge(a,attach,distance);edge(attach,b,w-distance);break
   distance-=w;attach=b
  edge(attach,leaf,limb)
 build(n);degrees=[];twos=0
 for x,neighbors in g.items():
  if x>=n:degrees.append(len(neighbors))
  for y,w in neighbors.items():
   if x<y:twos+=w-1
 degrees.extend([2]*twos);degrees.sort();out.append(' '.join(map(str,degrees)))
print('\n'.join(out))
