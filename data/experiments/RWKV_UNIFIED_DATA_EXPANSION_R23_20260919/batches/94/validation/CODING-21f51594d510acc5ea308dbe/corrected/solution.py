import sys
from collections import deque
lines=iter(sys.stdin.buffer);out=[];directions=((0,1),(1,0),(0,-1),(-1,0))
for line in lines:
 if not line.strip():continue
 rows,cols=map(int,line.split())
 if rows==0 and cols==0:break
 board=[next(lines).rstrip(b'\r\n') for _ in range(rows)];openings=[]
 for i in range(rows):
  for j in range(cols):
   if (i in (0,rows-1) or j in (0,cols-1)) and board[i][j]==46:openings.append((i,j))
 start,goal=openings;sr,sc=start;direction=1 if sr==0 else 3 if sr==rows-1 else 0 if sc==0 else 2;initial=(sr*cols+sc)*4+direction;distance=[10**9]*(rows*cols*4);distance[initial]=0;queue=deque([(initial,0)]);answer=-1
 while queue:
  state,cost=queue.popleft()
  if cost!=distance[state]:continue
  cell,d=divmod(state,4);r,c=divmod(cell,cols)
  if (r,c)==goal:answer=cost;break
  char=board[r][c]
  if char in (47,92):options=((3-d,int(char!=47)),(d^1,int(char!=92)))
  else:options=((d,0),)
  for direction,extra in options:
   dr,dc=directions[direction];nr=r+dr;nc=c+dc
   if not(0<=nr<rows and 0<=nc<cols) or board[nr][nc]==42:continue
   target=(nr*cols+nc)*4+direction;value=cost+extra
   if value<distance[target]:
    distance[target]=value
    if extra:queue.append((target,value))
    else:queue.appendleft((target,value))
 out.append(str(answer))
print('\n'.join(out))
