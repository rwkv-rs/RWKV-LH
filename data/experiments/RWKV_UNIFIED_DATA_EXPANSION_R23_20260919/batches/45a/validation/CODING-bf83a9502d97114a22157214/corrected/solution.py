import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));n,k,A,B,C=[next(it) for _ in range(5)];station=[next(it) for _ in range(n*n)];dist=[10**30]*(n*n*(k+1));dist[k]=0;heap=[(0,0,k)];end=n*n-1
while heap:
 cost,p,fuel=heapq.heappop(heap)
 if cost!=dist[p*(k+1)+fuel]:continue
 if p==end:print(cost);break
 r,c=divmod(p,n)
 if not station[p] and fuel<k:
  idx=p*(k+1)+k;new=cost+A+C
  if new<dist[idx]:dist[idx]=new;heapq.heappush(heap,(new,p,k))
 if not fuel:continue
 for dr,dc,fee in ((1,0,0),(0,1,0),(-1,0,B),(0,-1,B)):
  rr,cc=r+dr,c+dc
  if 0<=rr<n and 0<=cc<n:
   q=rr*n+cc;nf=k if station[q] else fuel-1;new=cost+fee+(A if station[q] else 0);idx=q*(k+1)+nf
   if new<dist[idx]:dist[idx]=new;heapq.heappush(heap,(new,q,nf))
