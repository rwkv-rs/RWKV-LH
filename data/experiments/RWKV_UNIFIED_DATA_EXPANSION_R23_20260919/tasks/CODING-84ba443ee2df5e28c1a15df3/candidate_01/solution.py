import sys
from array import array
def solve(n,operations):
 m=len(operations);inf=m+1;first=[inf]*n
 for time,op in enumerate(operations):
  if op[0]==1 and first[op[1]-1]==inf:first[op[1]-1]=time
 sparse=[first];length=1
 while length*2<=n:
  prev=sparse[-1];sparse.append([min(prev[i],prev[i+length]) for i in range(n-length*2+1)]);length*=2
 logs=[0]*(n+1)
 for i in range(2,n+1):logs[i]=logs[i//2]+1
 events={}
 for damage in range(1,n+1):
  at=-1;last=-1;count=0
  for start in range(0,n,damage):
   end=min(start+damage,n);level=logs[end-start];row=sparse[level];earliest=min(row[start],row[end-(1<<level)])
   if earliest==inf:break
   if earliest>at:at=earliest
   if at!=last:
    if count:events.setdefault(last,[]).append((damage,count))
    last=at;count=1
   else:count+=1
  if count:events.setdefault(last,[]).append((damage,count))
 tree=[0]*(n+1)
 def prefix(x):
  result=0
  while x:result+=tree[x];x-=x&-x
  return result
 out=[]
 for time,op in enumerate(operations):
  for damage,count in events.get(time,()):
   while damage<=n:tree[damage]+=count;damage+=damage&-damage
  if op[0]==2:
   _,left,right=op;out.append(str(right-left+1+prefix(right)-prefix(left-1)))
 return out
read=sys.stdin.buffer.readline;n,m=map(int,read().split());operations=[tuple(map(int,read().split())) for _ in range(m)];print('\n'.join(solve(n,operations)))
