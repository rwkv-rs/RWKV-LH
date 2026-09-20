import sys,bisect
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));queries=v[1:1+v[0]];digits=[0]*100000
for i in range(1,100000):digits[i]=digits[i//10]+i%10
rivers={i:array('Q',[i]) for i in (1,3,9)};out=[None]*len(queries)
def advance(x):
 y=x;value=x
 while y:value+=digits[y%100000];y//=100000
 return value
for n,index in sorted((n,i) for i,n in enumerate(queries)):
 river=9 if n%9==0 else 3 if n%3==0 else 1;sequence=rivers[river];x=n
 while sequence[-1]<x:sequence.append(advance(sequence[-1]))
 pos=bisect.bisect_left(sequence,x)
 while sequence[pos]!=x:
  if sequence[pos]<x:
   pos+=1
   if pos==len(sequence):sequence.append(advance(sequence[-1]))
  else:x=advance(x)
 out[index]=str(river)+' '+str(x)
print('\n'.join(out))
