import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n,d=next(it),next(it);h=[next(it) for i in range(n)]
 if abs(h[-1]-h[0])>d*(n-1):out.append('impossible');continue
 left=[-h[0]]*(n+1);right=[h[0]]*(n+1);addL=addR=minimum=0
 for i in range(1,n):
  addL-=d;addR+=d
  if i==n-1:break
  heapq.heappush(left,-(h[i]-addL));heapq.heappush(right,h[i]-addR);a=-left[0]+addL;b=right[0]+addR
  if a>b:
   minimum+=a-b;heapq.heapreplace(left,-(b-addL));heapq.heapreplace(right,a-addR)
 x=h[-1];answer=minimum+sum(max(0,-v+addL-x) for v in left)+sum(max(0,x-v-addR) for v in right);out.append(str(answer))
print('\n'.join(out))
