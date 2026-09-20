import sys
from functools import lru_cache
v=list(map(int,sys.stdin.buffer.read().split()));N=v[0];weights=v[1:];empty=(0,)*N
@lru_cache(None)
def advance(state,c,take):
 a=list(state);up=a[c];left=a[c-1] if c else 0
 if take:
  if up:
   label=up
   if left and left!=up:a=[up if x==left else x for x in a]
  elif left:label=left
  else:label=max(a)+1
  a[c]=label
 else:
  a[c]=0
  if up and up not in a:
   if any(a):return None
   return ()
 mapping={0:0};out=[]
 for x in a:
  if x not in mapping:mapping[x]=len(mapping)
  out.append(mapping[x])
 return tuple(out)
dp={empty:0};completed=None
for i,weight in enumerate(weights):
 c=i%N;new={}
 for state,value in dp.items():
  for take in (0,1):
   key=advance(state,c,take)
   if key is None:continue
   if key==():
    if completed is None or value>completed:completed=value
   else:
    score=value+weight*take
    if score>new.get(key,-10**30):new[key]=score
 dp=new
answer=completed
for state,value in dp.items():
 if len(set(state)-{0})==1 and (answer is None or value>answer):answer=value
print(answer)
