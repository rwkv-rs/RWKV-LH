import sys
from collections import deque
it=iter(sys.stdin.buffer.read().split());out=[]
for _ in range(int(next(it))):
 limit=int(next(it));n,m=int(next(it)),int(next(it));board=[next(it).decode() for _ in range(n+2)];start=board[-1].index('F');goal=board[0].index('G');q=deque([(n+1,start,0)]);seen={(n+1,start,0)};answer=None
 while q:
  r,c,t=q.popleft()
  if r==0 and c==goal:answer=t;break
  if t==limit:continue
  nt=t+1
  for dr,dc in ((0,0),(1,0),(-1,0),(0,1),(0,-1)):
   rr,cc=r+dr,c+dc
   if not(0<=rr<n+2 and 0<=cc<m):continue
   if 1<=rr<=n:
    direction=1 if (n-rr)%2==0 else -1
    if board[rr][(cc-direction*nt)%m]=='X':continue
   state=(rr,cc,nt%m)
   if state not in seen:seen.add(state);q.append((rr,cc,nt))
 out.append(f'The minimum number of turns is {answer}.' if answer is not None else 'The problem has no solution.')
print('\n'.join(out))
