import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));values=v[1:];maximum=max(values);counts=[0]*(maximum+1)
for x in values:counts[x]+=1
best=0
for x in range(1,maximum+1):
 if counts[x] and (x!=maximum or counts[x]>1):best=max(best,x//math.gcd(x,maximum)*maximum)
spf=list(range(maximum+1))
for p in range(2,math.isqrt(maximum)+1):
 if spf[p]==p:
  for x in range(p*p,maximum+1,p):
   if spf[x]==x:spf[x]=p
for divisor in range(1,maximum+1):
 if maximum*maximum//divisor<=best:break
 limit=maximum//divisor;quotients=[x for x in range(limit,0,-1) if counts[divisor*x]]
 if not quotients or divisor*quotients[0]*quotients[0]<=best:continue
 data=bytearray((limit+8)//8)
 for x in quotients:data[x//8]|=1<<(x%8)
 bits=int.from_bytes(data,'little');masks={};largest=quotients[0]
 for x in quotients:
  if divisor*x*largest<=best:break
  available=bits;remaining=x
  while remaining>1 and available:
   prime=spf[remaining]
   while remaining%prime==0:remaining//=prime
   if prime not in masks:
    number=limit//prime;pattern=1;span=1;offset=0;mask=0
    while number:
     if number&1:mask|=pattern<<(offset*prime);offset+=span
     number//=2
     if number:pattern|=pattern<<(span*prime);span*=2
    masks[prime]=mask<<prime
   available&=~masks[prime]
  if available:
   y=available.bit_length()-1
   if x!=y or counts[divisor*x]>1:best=max(best,divisor*x*y)
print(best)
