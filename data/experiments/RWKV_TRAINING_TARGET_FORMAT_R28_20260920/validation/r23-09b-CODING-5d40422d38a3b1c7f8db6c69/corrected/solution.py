import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=[x-1 for x in v[1:]];degree=[0]*n
for x in a:degree[x]+=1
queue=deque(i for i in range(n) if degree[i]==0);remaining=n
while queue:
 x=queue.popleft();remaining-=1;y=a[x];degree[y]-=1
 if degree[y]==0:queue.append(y)
print(remaining)
