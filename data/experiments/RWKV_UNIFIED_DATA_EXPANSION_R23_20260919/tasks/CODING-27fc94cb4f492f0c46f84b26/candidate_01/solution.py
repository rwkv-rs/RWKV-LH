import sys
from functools import lru_cache
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);requests=[(next(v),next(v)) for _ in range(n)]
@lru_cache(maxsize=50000)
def transitions(position,pickup,passengers):
 low=min(position,pickup);high=max(position,pickup);left={low};right={high}
 for floor in passengers:
  if floor<low:left.add(floor)
  if floor>high:right.add(floor)
 best={}
 for L in left:
  for R in right:
   remaining=tuple(x for x in passengers if x<L or x>R)
   if len(remaining)==4:continue
   cost=R-L+min(position-L+R-pickup,R-position+pickup-L)
   if cost<best.get(remaining,10**9):best[remaining]=cost
 return tuple(best.items())
dp={():0};position=1
for pickup,destination in requests:
 following={}
 for passengers,cost in dp.items():
  for remaining,movement in transitions(position,pickup,passengers):
   state=tuple(sorted(remaining+(destination,)));value=cost+movement
   if value<following.get(state,10**9):following[state]=value
 dp=following;position=pickup
answer=10**9
for passengers,cost in dp.items():
 if passengers:
  L=passengers[0];R=passengers[-1];cost+=R-L+min(abs(position-L),abs(position-R))
 answer=min(answer,cost)
print(answer+2*n)
