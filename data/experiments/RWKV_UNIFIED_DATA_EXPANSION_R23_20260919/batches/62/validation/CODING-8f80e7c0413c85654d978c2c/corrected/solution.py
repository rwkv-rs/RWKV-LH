import sys
v=sys.stdin.buffer.read().split();p=0;case=0;out=[]
while p<len(v):
 n,A,B=map(int,v[p:p+3]);p+=3
 if n==A==B==0:break
 case+=1;edges=[];adj={}
 for _ in range(n):u,w=int(v[p]),int(v[p+1]);r=float(v[p+2]);p+=3;edges.append((u,w,1/r));adj.setdefault(u,[]).append(w);adj.setdefault(w,[]).append(u)
 reachable={A};queue=[A]
 for u in queue:
  for w in adj.get(u,[]):
   if w not in reachable:reachable.add(w);queue.append(w)
 vertices=sorted(reachable-{B});index={u:i for i,u in enumerate(vertices)};N=len(vertices);matrix=[[0.0]*(N+1) for _ in range(N)]
 for u,w,g in edges:
  if u not in reachable:continue
  if u!=B:matrix[index[u]][index[u]]+=g
  if w!=B:matrix[index[w]][index[w]]+=g
  if u!=B and w!=B:matrix[index[u]][index[w]]-=g;matrix[index[w]][index[u]]-=g
 if A==B:answer=0.0
 else:
  matrix[index[A]][N]=1.0
  for col in range(N):
   pivot=max(range(col,N),key=lambda i:abs(matrix[i][col]));matrix[col],matrix[pivot]=matrix[pivot],matrix[col];row=matrix[col];scale=row[col]
   for j in range(col,N+1):row[j]/=scale
   for i in range(col+1,N):
    other=matrix[i];factor=other[col]
    for j in range(col,N+1):other[j]-=factor*row[j]
  x=[0.0]*N
  for i in range(N-1,-1,-1):x[i]=matrix[i][N]-sum(matrix[i][j]*x[j] for j in range(i+1,N))
  answer=x[index[A]]
 out.append('Case %d: %.2f Ohms'%(case,answer))
print('\n'.join(out))
