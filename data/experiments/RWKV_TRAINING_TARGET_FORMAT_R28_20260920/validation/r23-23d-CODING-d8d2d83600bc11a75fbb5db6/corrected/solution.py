import sys
v=sys.stdin.read().split();s=v[0];k=int(v[1]);x=y=0;points={(0,0)};step={'L':(-1,0),'R':(1,0),'U':(0,-1),'D':(0,1)}
for c in s:dx,dy=step[c];x+=dx;y+=dy;points.add((x,y))
dx,dy=x,y
if dx==0 and dy==0:print(len(points));raise SystemExit
if dx==0:points={(y,x) for x,y in points};dx,dy=dy,dx
if dx<0:points={(-x,y) for x,y in points};dx=-dx
groups={}
for x,y in points:
 q,r=divmod(x,dx);groups.setdefault((r,y-q*dy),[]).append(q)
answer=0
for values in groups.values():
 values.sort();left=values[0];right=left+k
 for q in values[1:]:
  if q>right:answer+=right-left;left=q;right=q+k
  else:right=max(right,q+k)
 answer+=right-left
print(answer)
