import sys,math
values=list(map(int,sys.stdin.buffer.read().split()));limit=math.isqrt(max(values,default=1));sieve=bytearray(b'\x01')*(limit+1)
if limit>=0:sieve[0]=0
if limit>=1:sieve[1]=0
for p in range(2,math.isqrt(limit)+1):
 if sieve[p]:sieve[p*p::p]=b'\x00'*((limit-p*p)//p+1)
primes=[p for p in range(2,limit+1) if sieve[p]]
def prime(x):
 if x<2:return False
 for p in primes:
  if p*p>x:return True
  if x%p==0:return x==p
 return True
out=[]
for n in values:
 pair=None
 if n%2:
  if n-2>2 and prime(n-2):pair=(2,n-2)
 else:
  p=n//2-1
  if p>2 and p%2==0:p-=1
  while p>=2:
   if prime(p) and prime(n-p):pair=(p,n-p);break
   p-=1 if p==3 else 2
 if pair:out.append(str(n)+' is the sum of '+str(pair[0])+' and '+str(pair[1])+'.')
 else:out.append(str(n)+' is not the sum of two primes!')
print('\n'.join(out))
