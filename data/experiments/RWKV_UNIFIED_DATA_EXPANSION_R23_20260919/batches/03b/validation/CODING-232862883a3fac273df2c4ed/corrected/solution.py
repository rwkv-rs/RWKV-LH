import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n,s,k=v[:3];raw=v[3:3+n];values=sorted(set(raw));s=len(values);index={x:i for i,x in enumerate(values)}
if k>=s:print(0);raise SystemExit
pair=[array('i',[0])*s for _ in range(s)];seen=[0]*s
for value in raw:
 y=index[value]
 for x in range(y):pair[x][y]+=seen[x]
 seen[y]+=1
cost=[array('i',[0])*s for _ in range(s)]
for right in range(1,s):
 total=0
 for left in range(right-1,-1,-1):total+=pair[left][right];cost[left][right]=cost[left][right-1]+total
inf=10**18;previous=[0]+[inf]*s
for groups in range(1,k+1):
 current=[inf]*(s+1)
 def solve(lo,hi,optlo,opthi):
  if lo>hi:return
  mid=(lo+hi)//2;best=inf;choice=-1
  for boundary in range(optlo,min(mid-1,opthi)+1):
   value=previous[boundary]+cost[boundary][mid-1]
   if value<best:best=value;choice=boundary
  current[mid]=best;solve(lo,mid-1,optlo,choice);solve(mid+1,hi,choice,opthi)
 solve(groups,s,groups-1,s-1);previous=current
print(previous[s])
