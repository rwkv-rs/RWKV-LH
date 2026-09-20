import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));m,k=v[:2];a=v[2:2+m];S=sum(a);counts=[0]*m
for x in v[2+m:]:counts[x-1]+=1
if k%S==0:print('forever');raise SystemExit
future=[];ready=[]
def push(i):
 j=counts[i]+1;release=(j-1)*S//a[i]+1;deadline=(j*S+a[i]-1)//a[i];heapq.heappush(future,(release,deadline,i))
for i in range(m):push(i)
end=(k//S+1)*S
for day in range(k+1,end+1):
 while future and future[0][0]<=day:
  release,deadline,i=heapq.heappop(future);heapq.heappush(ready,(deadline,i))
 if not ready:print(day-k-1);break
 deadline,i=heapq.heappop(ready)
 if deadline<day or (ready and ready[0][0]<=day):print(day-k-1);break
 counts[i]+=1;push(i)
else:print('forever')
