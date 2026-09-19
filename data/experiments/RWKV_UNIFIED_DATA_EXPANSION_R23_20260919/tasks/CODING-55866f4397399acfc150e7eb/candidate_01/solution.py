import sys,heapq
v=sys.stdin.read().split();at=0;queue=[]
while v[at]!='#':
 ident=int(v[at+1]);period=int(v[at+2]);queue.append((period,ident,period));at+=3
count=int(v[at+1]);heapq.heapify(queue);out=[]
for _ in range(count):
 time,ident,period=heapq.heappop(queue);out.append(str(ident));heapq.heappush(queue,(time+period,ident,period))
print('\n'.join(out))
