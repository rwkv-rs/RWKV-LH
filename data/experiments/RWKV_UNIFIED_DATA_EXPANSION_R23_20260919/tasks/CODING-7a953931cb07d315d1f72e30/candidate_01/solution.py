import sys

def prime(n):
 if n<2:return False
 for p in (2,3,5,7,11,13,17,19,23,29,31,37):
  if n%p==0:return n==p
 d=n-1;s=0
 while d%2==0:d//=2;s+=1
 for a in (2,325,9375,28178,450775,9780504,1795265022):
  if a%n==0:continue
  value=pow(a,d,n)
  if value in (1,n-1):continue
  for _ in range(s-1):
   value=value*value%n
   if value==n-1:break
  else:return False
 return True

def next_prime(x):
 if x<=2:return 2
 x|=1
 while not prime(x):x+=2
 return x

def next_power(x):
 best=next_prime(x+1);exponent=2
 while (1<<exponent)<best:
  lo=1;hi=1<<((x.bit_length()+exponent-1)//exponent)
  while lo<hi:
   middle=(lo+hi+1)//2
   if middle**exponent<=x:lo=middle
   else:hi=middle-1
  candidate=next_prime(lo+1)**exponent
  if candidate<best:best=candidate
  exponent+=1
 return best
n=int(sys.stdin.buffer.read())
if n<=2:print(n);raise SystemExit
best=next_power(n//2);bound=best//(n-best)
for quotient in range(2,bound+1):
 q=next_power(n//(quotient+1))
 if q<=n//quotient:best=min(best,quotient*q)
print(best)
