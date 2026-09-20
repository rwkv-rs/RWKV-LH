import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));n,m,army=next(it),next(it),next(it);a=[];b=[];c=[]
for i in range(n):a.append(next(it));b.append(next(it));c.append(next(it))
last=list(range(n))
for _ in range(m):u,v=next(it)-1,next(it)-1;last[v]=max(last[v],u)
buckets=[[] for i in range(n)]
for i in range(n):buckets[last[i]].append(c[i])
heap=[];score=0;possible=True
for i in range(n):
 while army<a[i] and heap:score-=heapq.heappop(heap);army+=1
 if army<a[i]:possible=False;break
 army+=b[i]
 for value in buckets[i]:heapq.heappush(heap,value);score+=value;army-=1
 while army<0:score-=heapq.heappop(heap);army+=1
print(score if possible else -1)
