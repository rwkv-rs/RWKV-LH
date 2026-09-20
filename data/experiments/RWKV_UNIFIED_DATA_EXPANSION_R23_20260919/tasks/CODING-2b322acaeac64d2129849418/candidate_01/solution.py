import sys,heapq,bisect
from collections import defaultdict
it=iter(map(int,sys.stdin.buffer.read().split()));MOD=998244353;out=[]
for _ in range(next(it)):
 n,Q,A=next(it),next(it),next(it);constraints=[(next(it)-1,next(it)-1,next(it)) for j in range(Q)];events=[[] for i in range(n)]
 for l,r,m in constraints:events[l].append((m,r))
 heap=[];positions=defaultdict(list)
 for i in range(n):
  for item in events[i]:heapq.heappush(heap,item)
  while heap and heap[0][1]<i:heapq.heappop(heap)
  cap=min(A,heap[0][0]) if heap else A;positions[cap].append(i)
 requirements={m:[0]*(len(ps)+1) for m,ps in positions.items()};valid=True
 for l,r,m in constraints:
  ps=positions.get(m,[]);a=bisect.bisect_left(ps,l)+1;b=bisect.bisect_right(ps,r)
  if a>b:valid=False;break
  requirements[m][b]=max(requirements[m][b],a)
 if not valid:out.append('0');continue
 answer=1
 for m,ps in positions.items():
  length=len(ps)
  if m==1:continue
  inverse=pow(m-1,MOD-2,MOD);weights=[1];total=1;first=0;required=0
  for i in range(1,length+1):
   added=total*inverse%MOD;weights.append(added);total=(total+added)%MOD;required=max(required,requirements[m][i])
   while first<required:total=(total-weights[first])%MOD;first+=1
  answer=answer*total%MOD*pow(m-1,length,MOD)%MOD
 out.append(str(answer))
print('\n'.join(out))
