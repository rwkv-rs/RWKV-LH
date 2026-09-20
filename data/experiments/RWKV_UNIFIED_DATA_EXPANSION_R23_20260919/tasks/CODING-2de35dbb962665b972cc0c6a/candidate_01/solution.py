import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(it),next(it);counts=[0]*(n+1);solved=bytearray(n+1);easy=[(0,i) for i in range(1,n+1)];hard=[(0,-i) for i in range(1,n+1)];heapq.heapify(hard);out=[];remaining=n
for _ in range(m):
 kind,p=next(it),next(it);counts[p]+=1
 if kind==1 and not solved[p]:solved[p]=1;remaining-=1
 if not solved[p]:heapq.heappush(easy,(-counts[p],p));heapq.heappush(hard,(counts[p],-p))
 if not remaining:out.append('Make noise');continue
 while solved[easy[0][1]] or -easy[0][0]!=counts[easy[0][1]]:heapq.heappop(easy)
 while solved[-hard[0][1]] or hard[0][0]!=counts[-hard[0][1]]:heapq.heappop(hard)
 out.append(f'{easy[0][1]} {-hard[0][1]}')
print('\n'.join(out))
