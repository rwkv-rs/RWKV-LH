import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);q=next(it);edges=[None]+[(next(it)-1,next(it)-1) for _ in range(m)];queries=[(next(it),next(it)) for _ in range(q)]
parent=[-1]*n;parity=[0]*n;history=[]
def add(index):
 a,b=edges[index];pa=pb=0
 while parent[a]>=0:pa^=parity[a];a=parent[a]
 while parent[b]>=0:pb^=parity[b];b=parent[b]
 if a==b:return pa!=pb
 if parent[a]>parent[b]:a,b=b,a
 history.append((a,parent[a],b,parent[b]));parent[a]+=parent[b];parent[b]=a;parity[b]=pa^pb^1;return True
def rollback(mark):
 while len(history)>mark:
  a,sa,b,sb=history.pop();parent[a]=sa;parent[b]=sb;parity[b]=0
first=m+1
for i in range(1,m+1):
 if not add(i):first=i;break
rollback(0)
if first==m+1:print('\n'.join(['NO']*q));raise SystemExit
threshold=[m+1]*(m+1)
def solve(lo,hi,lower,upper):
 if lo>hi:return
 mid=(lo+hi)//2;mark=len(history)
 for i in range(lo,mid):add(i)
 found=lower
 for i in range(upper,lower,-1):
  if not add(i):found=i;break
 threshold[mid]=found;rollback(mark)
 if lo<mid:
  for i in range(found+1,upper+1):add(i)
  solve(lo,mid-1,lower,found);rollback(mark)
 if mid<hi:
  for i in range(lo,mid+1):add(i)
  solve(mid+1,hi,found,upper);rollback(mark)
solve(1,first,0,m)
print('\n'.join('YES' if r<threshold[l] else 'NO' for l,r in queries))
