import sys
from functools import lru_cache
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];values=sorted(v[1:]);leaves=values.count(1);internal=tuple(x for x in values if x>1)
if values[-1]!=n or values.count(n)!=1 or 2 in values or (internal and leaves<len(internal)+1):print('NO');raise SystemExit
@lru_cache(None)
def construct(index,forest):
 if index==len(internal):return forest==(n,)
 target=internal[index]-1;counts={}
 for x in forest:counts[x]=counts.get(x,0)+1
 kinds=sorted((x for x in counts if x>1 and x<=target),reverse=True);chosen={}
 def select(pos,remaining,number):
  if pos==len(kinds):
   if remaining>counts.get(1,0) or number+remaining<2:return False
   chosen[1]=remaining;nextforest=[]
   for x,c in counts.items():nextforest.extend([x]*(c-chosen.get(x,0)))
   nextforest.append(internal[index]);return construct(index+1,tuple(sorted(nextforest)))
  x=kinds[pos]
  for take in range(min(counts[x],remaining//x),-1,-1):
   chosen[x]=take
   if select(pos+1,remaining-take*x,number+take):return True
  chosen.pop(x,None);return False
 return select(0,target,0)
print('YES' if construct(0,(1,)*leaves) else 'NO')
