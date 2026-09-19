import sys,math
v=iter(map(int,sys.stdin.read().split()));n=next(v);k=next(v);points=[(next(v),next(v)) for _ in range(n)];distance=[10**30]*n;distance[0]=0;used=[False]*n;edges=[]
for step in range(n):
 p=min((i for i in range(n) if not used[i]),key=distance.__getitem__);used[p]=True
 if step:edges.append(distance[p])
 x,y=points[p]
 for j,(xx,yy) in enumerate(points):
  if not used[j]:distance[j]=min(distance[j],(x-xx)**2+(y-yy)**2)
edges.sort();print(f'{math.sqrt(edges[n-k]):.2f}')
