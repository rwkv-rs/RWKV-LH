import sys
from collections import deque
a=list(map(int,sys.stdin.buffer.read().split()));n,w,b,x=a[:4];counts=a[4:4+n];costs=a[4+n:4+2*n];dp=[w]
for index,(count,cost) in enumerate(zip(counts,costs)):
 if index:dp=[min(w+j*b,mana+x) if mana>=0 else -1 for j,mana in enumerate(dp)]
 next_dp=[-1]*(len(dp)+count);queue=deque()
 for j in range(len(next_dp)):
  if j<len(dp) and dp[j]>=0:
   value=dp[j]+j*cost
   while queue and queue[-1][1]<=value:queue.pop()
   queue.append((j,value))
  while queue and queue[0][0]<j-count:queue.popleft()
  if queue:
   mana=queue[0][1]-j*cost
   if mana>=0:next_dp[j]=mana
 while len(next_dp)>1 and next_dp[-1]<0:next_dp.pop()
 dp=next_dp
print(max(j for j,mana in enumerate(dp) if mana>=0))
