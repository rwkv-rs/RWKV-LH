import sys,heapq
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 a=next(v);b=next(v);c=next(v);n=next(v);low=[-1];high=[];total=1
 for i in range(2,n+1):
  x=(a*(-low[0])+b*i+c)%1000000007;total+=x
  if x<=-low[0]:heapq.heappush(low,-x)
  else:heapq.heappush(high,x)
  if len(low)>len(high)+1:heapq.heappush(high,-heapq.heappop(low))
  elif len(high)>len(low):heapq.heappush(low,-heapq.heappop(high))
 out.append(str(total))
print('\n'.join(out))
