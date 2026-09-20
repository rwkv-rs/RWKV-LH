import sys
from functools import lru_cache

def solve(h,w):
 if h*w%2:return 0
 if h<w:h,w=w,h
 full=(1<<w)-1
 @lru_cache(None)
 def transitions(incoming,previous,first):
  forced=0 if first else ((1<<(w-1))-1)&~(incoming|(incoming>>1)|previous)
  # Every uncovered interior vertex must be crossed by a current horizontal domino.
  if forced&(forced<<1):return ()
  occupied=incoming;horizontal=forced
  cells=forced|(forced<<1)
  if cells&occupied:return ()
  occupied|=cells;answer=[]
  def fill(used,down,across):
   if used==full:answer.append((down,across));return
   bit=(~used&full)&-(~used&full)
   fill(used|bit,down|bit,across)
   other=bit<<1
   if other<=full and not used&other:fill(used|bit|other,down,across|bit)
  fill(occupied,0,horizontal)
  return tuple(answer)
 dp={(0,0):1}
 for row in range(h):
  following={}
  for (incoming,previous),ways in dp.items():
   for down,across in transitions(incoming,previous,row==0):
    if row==h-1 and down:continue
    key=(down,across);following[key]=following.get(key,0)+ways
  dp=following
 return sum(dp.values())
v=iter(map(int,sys.stdin.buffer.read().split()));output=[];cache={}
for h in v:
 w=next(v)
 if h==w==0:break
 key=tuple(sorted((h,w)))
 if key not in cache:cache[key]=solve(h,w)
 output.append(str(cache[key]))
print('\n'.join(output))
