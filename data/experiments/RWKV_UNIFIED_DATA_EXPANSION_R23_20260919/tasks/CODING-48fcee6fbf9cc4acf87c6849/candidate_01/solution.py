import sys
from array import array
a=list(map(int,sys.stdin.buffer.read().split()));queries=list(zip(a[1::2],a[2::2]));limit=max(x for x,y in queries);spf=array('I',[0])*(limit+1)
for p in range(2,int(limit**0.5)+1):
 if spf[p]==0:
  for q in range(p*p,limit+1,p):
   if spf[q]==0:spf[q]=p
omega=bytearray(limit+1);prefix=array('I',[0])*(limit+1)
for i in range(2,limit+1):
 omega[i]=omega[i//spf[i]]+1 if spf[i] else 1;prefix[i]=prefix[i-1]+omega[i]
print('\n'.join(str(prefix[x]-prefix[y]) for x,y in queries))
