import sys,heapq
v=iter(sys.stdin.read().split());out=[];case=0
while True:
 n=int(next(v));r=int(next(v))
 if n==0 and r==0:break
 g={}
 for _ in range(r):
  a=next(v);b=next(v);w=int(next(v));g.setdefault(a,[]).append((b,w));g.setdefault(b,[]).append((a,w))
 start=next(v);finish=next(v);best={start:10**30};heap=[(-best[start],start)]
 while heap:
  negative,a=heapq.heappop(heap);capacity=-negative
  if best.get(a)!=capacity:continue
  if a==finish:break
  for b,w in g.get(a,[]):
   candidate=min(capacity,w)
   if candidate>best.get(b,-1):best[b]=candidate;heapq.heappush(heap,(-candidate,b))
 case+=1;out.append(f'Scenario #{case}\n{best.get(finish,0)} tons')
print('\n\n'.join(out))
