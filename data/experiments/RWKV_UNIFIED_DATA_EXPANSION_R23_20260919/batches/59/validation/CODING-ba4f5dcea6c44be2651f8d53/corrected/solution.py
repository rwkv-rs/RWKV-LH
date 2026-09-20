import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));limit=math.isqrt(max(2*x+1 for x in v[3::3]));sieve=bytearray(b'\1')*(limit+1);primes=[]
for p in range(2,limit+1):
 if sieve[p]:
  primes.append(p)
  if p*p<=limit:sieve[p*p:limit+1:p]=b'\0'*((limit-p*p)//p+1)
out=[]
for A,B,K in zip(v[1::3],v[2::3],v[3::3]):
 number=2*K+1;factors=[]
 for p in primes:
  if p*p>number:break
  if number%p==0:
   exponent=0;power=1
   while number%p==0:number//=p;exponent+=1;power*=p
   factors.append((p,exponent,power))
 if number>1:factors.append((number,1,number))
 answer=1
 for p,e,q in factors:
  b=B%q
  if b==0:answer*=p**(e-(e+A-1)//A);continue
  valuation=0
  while b%p==0:b//=p;valuation+=1
  if valuation%A:answer=0;break
  t=valuation//A;mod=p**(e-valuation);phi=mod//p*(p-1);g=math.gcd(A,phi)
  if pow(b,phi//g,mod)!=1:answer=0;break
  answer*=g*p**(valuation-t)
 out.append(str(answer))
print('\n'.join(out))
