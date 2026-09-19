import sys,math
n=int(sys.stdin.buffer.read());size=(n+1)//2;sieve=bytearray(b'\1')*size
if size:sieve[0]=0
for p in range(3,math.isqrt(n)+1,2):
 if sieve[p//2]:
  start=p*p//2;sieve[start::p]=b'\0'*((size-1-start)//p+1)
print(sum(sieve)+(n>=2))
