import sys,math
l,r=map(int,sys.stdin.buffer.read().split());bound=math.isqrt(r);prime=bytearray(b'\1')*(bound+1)
if bound>=0:prime[0]=0
if bound>=1:prime[1]=0
for p in range(2,math.isqrt(bound)+1):
 if prime[p]:prime[p*p:bound+1:p]=b'\0'*((bound-p*p)//p+1)
start=max(l,5);start+=(1-start)%4;answer=int(l<=2<=r)
if start<=r:
 length=(r-start)//4+1;valid=bytearray(b'\1')*length
 for p in range(3,bound+1,2):
  if not prime[p]:continue
  first=max(p*p,((start+p-1)//p)*p)
  while first%4!=1:first+=p
  if first>r:continue
  index=(first-start)//4;valid[index::p]=b'\0'*((length-1-index)//p+1)
 answer+=sum(valid)
print(answer)
