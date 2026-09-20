import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));n,w=next(it),next(it);answer=[0]*w;diff=[0]*(w+1)
for _ in range(n):
 length=next(it);a=[next(it) for _ in range(length)];slack=w-length
 if length*2<=w:
  best=0
  for j,x in enumerate(a):best=max(best,x);answer[j]+=best
  diff[length]+=best;diff[w-length]-=best;best=0
  for j in range(length-1,-1,-1):best=max(best,a[j]);answer[slack+j]+=best
 else:
  q=deque();right=-1
  for j in range(w):
   upper=min(length-1,j);lower=max(0,j-slack)
   while right<upper:
    right+=1
    while q and a[q[-1]]<=a[right]:q.pop()
    q.append(right)
   while q[0]<lower:q.popleft()
   best=a[q[0]]
   if j<slack or j>=length:best=max(0,best)
   answer[j]+=best
value=0
for j in range(w):value+=diff[j];answer[j]+=value
print(' '.join(map(str,answer)))
