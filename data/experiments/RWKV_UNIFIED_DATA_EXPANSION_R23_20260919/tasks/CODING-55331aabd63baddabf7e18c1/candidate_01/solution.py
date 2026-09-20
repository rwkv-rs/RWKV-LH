import sys,heapq,bisect
v=list(map(int,sys.stdin.buffer.read().split()));p=1;cases=[];maximum=1
for _ in range(v[0]):
 n=v[p];p+=1;a=v[p:p+n];p+=n;cases.append(a);maximum=max(maximum,max(a))
boundaries=[0,1];grundy=[0,1];events=[2,3,4,5,6];queued=set(events)
while events:
 x=heapq.heappop(events);queued.remove(x)
 if x>maximum:break
 options={grundy[bisect.bisect_right(boundaries,x//d)-1] for d in range(2,7)};g=0
 while g in options:g+=1
 if g!=grundy[-1]:
  boundaries.append(x);grundy.append(g)
  for d in range(2,7):
   event=x*d
   if event<=maximum and event not in queued:heapq.heappush(events,event);queued.add(event)
out=[]
for a in cases:
 value=0
 for x in a:value^=grundy[bisect.bisect_right(boundaries,x)-1]
 out.append('Henry' if value else 'Derek')
print('\n'.join(out))
