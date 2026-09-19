import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];b=v[n+1:];heap=[(-b[i],i) for i in range(n) if b[i]>a[i]];heapq.heapify(heap);answer=0
if any(x<y for x,y in zip(b,a)):print(-1);raise SystemExit
while heap:
 neg,i=heapq.heappop(heap)
 if -neg!=b[i] or b[i]==a[i]:continue
 step=b[(i-1)%n]+b[(i+1)%n];count=(b[i]-a[i])//step
 if count==0:print(-1);raise SystemExit
 b[i]-=count*step;answer+=count
 if b[i]>a[i]:heapq.heappush(heap,(-b[i],i))
print(answer)
