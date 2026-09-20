import sys
data=list(map(int,sys.stdin.buffer.read().split()));a=data[1:];total=sum(a);place=1;answer=0
while place<=total:
 modulus=10*place;minimum=[None]*10;maximum=[None]*10;minimum[0]=maximum[0]=0;best=0
 for value in a:
  residue=value%modulus;states=[x for pair in zip(minimum,maximum) for x in pair if x is not None];oldmin=minimum[:];oldmax=maximum[:]
  for x in states:
   y=(x+residue)%modulus;bucket=y//place
   if oldmin[bucket] is None or y<oldmin[bucket]:oldmin[bucket]=y
   if oldmax[bucket] is None or y>oldmax[bucket]:oldmax[bucket]=y
  minimum,maximum=oldmin,oldmax
  if minimum[9] is not None:best=9;break
 else:best=max(i for i in range(10) if minimum[i] is not None)
 answer+=best;place*=10
print(answer)
