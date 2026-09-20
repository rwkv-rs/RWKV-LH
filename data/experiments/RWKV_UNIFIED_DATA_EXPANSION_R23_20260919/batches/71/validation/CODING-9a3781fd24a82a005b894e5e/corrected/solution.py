import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];limit=2000000;prime=bytearray(b'\x01')*(limit+1);prime[:2]=b'\x00\x00'
for p in range(2,math.isqrt(limit)+1):
 if prime[p]:prime[p*p:limit+1:p]=b'\x00'*((limit-p*p)//p+1)
primes=[i for i in range(2,limit+1) if prime[i]];blocked=bytearray(limit+1);out=[];greater=False;position=0
for x in a:
 if greater:
  while blocked[primes[position]]:position+=1
  y=primes[position];position+=1;out.append(y);blocked[y]=1;continue
 y=x
 while blocked[y]:y+=1
 greater=y>x;out.append(y);remaining=y;factors=[]
 for p in primes:
  if p*p>remaining:break
  if remaining%p==0:
   factors.append(p)
   while remaining%p==0:remaining//=p
 if remaining>1:factors.append(remaining)
 for p in factors:blocked[p:limit+1:p]=b'\x01'*((limit-p)//p+1)
print(*out)
