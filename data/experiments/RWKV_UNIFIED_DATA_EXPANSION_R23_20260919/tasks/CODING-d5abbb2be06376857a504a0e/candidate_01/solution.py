import sys
from functools import lru_cache
v=sys.stdin.buffer.read().split();n=int(v[0]);cost=list(map(int,v[1:5]));grid=v[5:9];options=[[] for _ in range(4)]
for row in range(4):
 for size in range(1,5):
  for top in range(max(0,row-size+1),min(row,4-size)+1):options[row].append((size,top))
@lru_cache(None)
def transitions(state,mask):
 uncovered=mask
 for row,x in enumerate(state):
  if x:uncovered&=~(1<<row)
 if not uncovered:return ((tuple(max(0,x-1) for x in state),0),)
 row=(uncovered&-uncovered).bit_length()-1;answers={}
 for size,top in options[row]:
  new=list(state)
  for r in range(top,top+size):new[r]=max(new[r],size)
  for target,extra in transitions(tuple(new),mask):
   value=cost[size-1]+extra
   if value<answers.get(target,10**30):answers[target]=value
 return tuple(answers.items())
dp={(0,0,0,0):0}
for column in range(n):
 mask=sum(1<<row for row in range(4) if grid[row][column]==42);new={}
 for state,value in dp.items():
  for target,extra in transitions(state,mask):
   result=value+extra
   if result<new.get(target,10**30):new[target]=result
 dp=new
print(min(dp.values()))
