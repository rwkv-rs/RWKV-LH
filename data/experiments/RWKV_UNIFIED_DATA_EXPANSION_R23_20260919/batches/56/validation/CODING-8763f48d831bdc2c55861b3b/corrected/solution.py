import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:]
if max(a)<=2*min(a):print(*([-1]*n));raise SystemExit
b=a*3;q=deque();right=0;answer=[]
for left in range(n):
 while right<len(b) and (not q or 2*b[right]>=b[q[0]]):
  while q and b[q[-1]]<=b[right]:q.pop()
  q.append(right);right+=1
 answer.append(right-left)
 if q and q[0]==left:q.popleft()
print(*answer)
