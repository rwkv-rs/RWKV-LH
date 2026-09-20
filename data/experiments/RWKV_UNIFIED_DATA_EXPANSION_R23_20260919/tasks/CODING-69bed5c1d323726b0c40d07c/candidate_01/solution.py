import sys,bisect
def solve(points,t):
 points=sorted(points);n=len(points)
 def area(s):
  w=2*s+1;events=sorted([(x,1,y) for x,y in points]+[(x+w,-1,y) for x,y in points]);active=[];covered=0;total=0;previous=events[0][0]
  for x,kind,y in events:
   total+=(x-previous)*covered;previous=x;pos=bisect.bisect_left(active,y)
   if kind==1:
    if not active:covered=w
    elif pos==0:covered+=min(active[0]-y,w)
    elif pos==len(active):covered+=min(y-active[-1],w)
    else:covered+=min(y-active[pos-1],w)+min(active[pos]-y,w)-min(active[pos]-active[pos-1],w)
    active.insert(pos,y)
   else:
    if len(active)==1:covered=0
    elif pos==0:covered-=min(active[1]-y,w)
    elif pos==len(active)-1:covered-=min(y-active[pos-1],w)
    else:covered-=min(y-active[pos-1],w)+min(active[pos+1]-y,w)-min(active[pos+1]-active[pos-1],w)
    active.pop(pos)
  return total
 boundaries={0,t}
 for i,(x,y) in enumerate(points):
  for a,b in points[:i]:
   for difference in (abs(x-a),abs(y-b)):
    cut=difference//2
    if 0<cut<t:boundaries.add(cut)
 bounds=sorted(boundaries);summed=0
 for start,end in zip(bounds,bounds[1:]):
  length=end-start;a=area(start);summed+=length*a
  if length>=2:
   b=area(start+1);summed+=(b-a)*length*(length-1)//2
   if length>=3:summed+=(area(start+2)-2*b+a)*length*(length-1)*(length-2)//6
 return (t*area(t)-summed)%998244353
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);t=next(v);print(solve([(next(v),next(v)) for _ in range(n)],t))
