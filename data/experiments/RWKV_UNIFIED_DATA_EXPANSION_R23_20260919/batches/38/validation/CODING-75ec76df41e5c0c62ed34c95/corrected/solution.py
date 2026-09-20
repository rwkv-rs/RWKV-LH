import sys
from collections import deque
read=sys.stdin.buffer.readline;cases=int(read());out=[];dirs=((-1,0),(0,1),(1,0),(0,-1));symbols='^>v<'
for case in range(1,cases+1):
 h,w=map(int,read().split());grid=[read().strip().decode() for _ in range(h)];bad=[set() for _ in range(4)];turrets=[]
 for r in range(h):
  for c in range(w):
   value=grid[r][c]
   if value=='S':start=(r,c)
   elif value=='G':goal=(r,c)
   elif value in symbols:turrets.append((r,c,symbols.index(value)))
 for phase in range(4):
  for r,c,d in turrets:
   dr,dc=dirs[(d+phase)%4];r+=dr;c+=dc
   while 0<=r<h and 0<=c<w and grid[r][c] not in '#^>v<':bad[phase].add((r,c));r+=dr;c+=dc
 q=deque([(start[0],start[1],0)]);seen={(start[0],start[1],0)};answer=None
 while q:
  r,c,time=q.popleft()
  if (r,c)==goal:answer=time;break
  phase=(time+1)%4
  for dr,dc in dirs:
   rr,cc=r+dr,c+dc;state=(rr,cc,phase)
   if 0<=rr<h and 0<=cc<w and grid[rr][cc] not in '#^>v<' and (rr,cc) not in bad[phase] and state not in seen:seen.add(state);q.append((rr,cc,time+1))
 out.append(f'Case #{case}: '+('impossible' if answer is None else str(answer)))
print('\n'.join(out))
