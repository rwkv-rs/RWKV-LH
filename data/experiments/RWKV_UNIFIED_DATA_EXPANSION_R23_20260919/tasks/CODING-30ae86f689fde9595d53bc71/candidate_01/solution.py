import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));p=1;out=[]
for _ in range(v[0]):
 n=v[p];p+=1;a=v[p:p+n];b=v[p+n:p+2*n];p+=2*n;frequency=[0]*(n+1)
 for x in a:frequency[x]+=1
 common=max(range(1,n+1),key=frequency.__getitem__);graph=[[] for _ in range(n+1)];degree=[0]*(n+1);edges=0
 for x,y in zip(a,b):
  if x!=common and y!=common:graph[x].append(y);degree[y]+=1;edges+=1
 queue=deque(i for i in range(1,n+1) if i!=common and degree[i]==0);removed=0
 while queue:
  u=queue.popleft()
  for w in graph[u]:
   removed+=1;degree[w]-=1
   if degree[w]==0:queue.append(w)
 out.append('AC' if removed==edges else 'WA')
print('\n'.join(out))
