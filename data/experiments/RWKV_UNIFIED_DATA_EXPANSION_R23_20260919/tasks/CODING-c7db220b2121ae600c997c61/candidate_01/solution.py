import sys,heapq,bisect
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];length=[x+1 for x in v[1:n+1]];r1,c1,r2,c2=v[n+1:];r1-=1;r2-=1;columns=sorted(set([1,c1,c2]+length));width=len(columns);end=[bisect.bisect_left(columns,x) for x in length];start=r1*width+bisect.bisect_left(columns,c1);target=r2*width+bisect.bisect_left(columns,c2);distance=[10**30]*(n*width);distance[start]=0;queue=[(0,start)]
while queue:
 d,u=heapq.heappop(queue)
 if d!=distance[u]:continue
 if u==target:print(d);break
 row,col=divmod(u,width);edges=[]
 if col:edges.append((u-1,columns[col]-columns[col-1]))
 if col<end[row]:edges.append((u+1,columns[col+1]-columns[col]))
 if row:edges.append(((row-1)*width+min(col,end[row-1]),1))
 if row+1<n:edges.append(((row+1)*width+min(col,end[row+1]),1))
 for w,cost in edges:
  nd=d+cost
  if nd<distance[w]:distance[w]=nd;heapq.heappush(queue,(nd,w))
