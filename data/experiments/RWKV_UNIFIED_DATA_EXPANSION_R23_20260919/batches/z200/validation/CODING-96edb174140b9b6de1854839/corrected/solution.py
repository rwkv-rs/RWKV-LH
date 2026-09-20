import sys
from functools import lru_cache
v=sys.stdin.buffer.read().split();H,W,K=map(int,v[:3]);grid=[s.decode() for s in v[3:]]
if not H or not W:print(0);raise SystemExit
if W>H:grid=[''.join(grid[r][c] for r in range(H)) for c in range(W)];H,W=W,H
@lru_cache(None)
def advance(state,closed,previous,c,colour):
 if closed&(1 if colour==1 else 2):return None
 up=state[c];left=state[c-1] if c else 0
 if c and previous==colour and up*colour>0 and left*colour>0:return None
 a=list(state)
 if up*colour>0:
  label=up
  if left*colour>0 and left!=up:a=[up if x==left else x for x in a]
 elif left*colour>0:label=left
 else:label=colour*(max(map(abs,a),default=0)+1)
 a[c]=label
 if up and up not in a and up*colour<0:
  if any(x*up>0 for x in a):return None
  closed|=1 if up>0 else 2
 mapping={};canon=[];pos=0;neg=0
 for x in a:
  if not x:canon.append(0);continue
  if x not in mapping:
   if x>0:pos+=1;mapping[x]=pos
   else:neg-=1;mapping[x]=neg
  canon.append(mapping[x])
 return tuple(canon),closed,(1 if up>0 else -1 if up<0 else 0)
B=72;dp={((0,)*W,0,0):1}
for r in range(H):
 for c in range(W):
  choices=(1,) if grid[r][c]=='T' else (-1,) if grid[r][c]=='D' else (1,-1);new={}
  for (state,closed,previous),poly in dp.items():
   for colour in choices:
    key=advance(state,closed,previous,c,colour)
    if key is not None:new[key]=new.get(key,0)+(poly<<B if colour==1 else poly)
  dp=new
total=0;mask=(1<<B)-1;cells=H*W
for (state,closed,previous),poly in dp.items():
 positive={x for x in state if x>0};negative={x for x in state if x<0}
 if len(positive)+bool(closed&1)!=1 or len(negative)+bool(closed&2)!=1:continue
 for count in range(1,cells):
  if abs(2*count-cells)<=K:total+=(poly>>(B*count))&mask
print(total)
