import sys
from collections import deque
v=iter(map(int,sys.stdin.read().split()));n=next(v);moves=[]
for _ in range(2):moves.append([next(v) for j in range(next(v))])
state=[[0]*n for _ in range(2)];remaining=[[len(moves[p])]*n for p in range(2)];q=deque()
for p in range(2):state[p][0]=-1;q.append((p,0))
while q:
 p,x=q.popleft();other=1-p
 for step in moves[other]:
  y=(x-step)%n
  if state[other][y]:continue
  if state[p][x]==-1:state[other][y]=1;q.append((other,y))
  else:
   remaining[other][y]-=1
   if remaining[other][y]==0:state[other][y]=-1;q.append((other,y))
for p in range(2):print(' '.join({0:'Loop',1:'Win',-1:'Lose'}[x] for x in state[p][1:]))
