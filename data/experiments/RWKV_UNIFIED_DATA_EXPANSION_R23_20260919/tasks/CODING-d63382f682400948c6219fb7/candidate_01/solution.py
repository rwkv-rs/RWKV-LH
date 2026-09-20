import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m,k=v[:3];points=list(zip(v[3::2],v[4::2]));index={p:i for i,p in enumerate(points)};parent=list(range(k));flags=[int(x==0 or y==m-1)+2*int(y==0 or x==n-1) for x,y in points]
def find(a):
 while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
 return a
def union(a,b):
 a,b=find(a),find(b)
 if a!=b:parent[b]=a;flags[a]|=flags[b]
for i,(x,y) in enumerate(points):
 for dx in (-1,0,1):
  for dy in (-1,0,1):
   j=index.get((x+dx,y+dy))
   if j is not None:union(i,j)
if any(flags[find(i)]==3 for i in range(k)):print(0);raise SystemExit
candidates={(0,1),(1,0),(n-2,m-1),(n-1,m-2)}
for x,y in points:
 for dx in (-1,0,1):
  for dy in (-1,0,1):candidates.add((x+dx,y+dy))
for x,y in candidates:
 if not(0<=x<n and 0<=y<m) or (x,y) in index or (x,y) in ((0,0),(n-1,m-1)):continue
 flag=int(x==0 or y==m-1)+2*int(y==0 or x==n-1)
 for dx in (-1,0,1):
  for dy in (-1,0,1):
   j=index.get((x+dx,y+dy))
   if j is not None:flag|=flags[find(j)]
 if flag==3:print(1);raise SystemExit
print(2)
