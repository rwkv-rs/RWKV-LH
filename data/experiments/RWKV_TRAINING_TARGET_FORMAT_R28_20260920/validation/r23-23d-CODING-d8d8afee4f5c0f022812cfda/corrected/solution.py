import sys,heapq
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);a=sorted((next(v),next(v)) for i in range(n));heap=[];paid=0;cost=0
 for i in range(n-1,-1,-1):
  threshold,price=a[i];heapq.heappush(heap,price)
  while paid+i<threshold:cost+=heapq.heappop(heap);paid+=1
 out.append(str(cost))
print('\n'.join(out))
