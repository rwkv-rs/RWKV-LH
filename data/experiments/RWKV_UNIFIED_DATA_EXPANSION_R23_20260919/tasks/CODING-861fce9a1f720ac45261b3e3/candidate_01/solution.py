import sys,math
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];limit=2000000;spf=array('i',[0])*(limit+1)
for p in range(2,math.isqrt(limit)+1):
 if not spf[p]:
  for j in range(p*p,limit+1,p):
   if not spf[j]:spf[j]=p
blocked=bytearray(limit+1);greater=False;pointer=2;out=[]
for x in a:
 y=pointer if greater else x
 while blocked[y]:y+=1
 if y>x:greater=True
 out.append(y);remaining=y
 while remaining>1:
  p=spf[remaining] or remaining;blocked[p::p]=b'\x01'*(limit//p)
  while remaining%p==0:remaining//=p
 if greater:pointer=y+1
print(' '.join(map(str,out)))
