import sys
from collections import Counter
v=sys.stdin.buffer.read().split();T,C=map(int,v[:2]);targets=set(map(int,v[2:2+T]));commands=v[2+T].decode();position=[];x=0;counts=[Counter() for _ in range(5)]
for ch in commands:
 position.append(x)
 if ch=='F':
  for j in range(5):
   y=x+j-2
   if y in targets:counts[j][y]+=1
 else:x+=1 if ch=='R' else -1
remaining=list(map(len,counts));prefix=set();answer=remaining[2];move={'L':-1,'F':0,'R':1}
for x,ch in zip(position,commands):
 if ch=='F':
  for j in range(5):
   y=x+j-2
   if y in counts[j]:
    counts[j][y]-=1
    if not counts[j][y]:del counts[j][y];remaining[j]-=int(y not in prefix)
 for new in 'LFR':
  j=move[new]-move[ch]+2;candidate=len(prefix)+remaining[j]
  if new=='F' and x in targets and x not in prefix and x not in counts[j]:candidate+=1
  answer=max(answer,candidate)
 if ch=='F' and x in targets and x not in prefix:
  prefix.add(x)
  for j in range(5):remaining[j]-=int(x in counts[j])
print(answer)
