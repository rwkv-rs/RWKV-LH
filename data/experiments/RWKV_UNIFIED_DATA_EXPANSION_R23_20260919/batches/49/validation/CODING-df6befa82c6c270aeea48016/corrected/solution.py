import sys
v=sys.stdin.buffer.read().split();n,m,k=map(int,v[:3]);board=v[3:3+n];commands=v[3+n].decode();free=0;target=0
for r,row in enumerate(board):
 for c,ch in enumerate(row):
  if ch!=35:free|=1<<(r*m+c)
  if ch==69:target=1<<(r*m+c)
state=free;blocked={'R':free&~(free>>1),'L':free&~(free<<1),'D':free&~(free>>m),'U':free&~(free<<m)}
if state==target:print(0)
else:
 for i,ch in enumerate(commands,1):
  if ch=='R':moved=state<<1
  elif ch=='L':moved=state>>1
  elif ch=='D':moved=state<<m
  else:moved=state>>m
  state=(moved&free)|(state&blocked[ch])
  if state==target:print(i);break
 else:print(-1)
