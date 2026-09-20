import sys,math
from functools import lru_cache
def prime(n):
 if n<2:return False
 for p in (2,3,5,7,11,13,17,19,23,29,31,37):
  if n%p==0:return n==p
 d=n-1;s=0
 while d%2==0:d//=2;s+=1
 for a in (2,325,9375,28178,450775,9780504,1795265022):
  if a%n==0:continue
  x=pow(a,d,n)
  if x in (1,n-1):continue
  for _ in range(s-1):
   x=x*x%n
   if x==n-1:break
  else:return False
 return True
@lru_cache(None)
def smallest(n):
 if prime(n):return n
 for p in (2,3,5,7,11,13):
  if n%p==0:return p
 c=1
 while True:
  x=y=2;g=1
  while g==1:x=(x*x+c)%n;y=(y*y+c)%n;y=(y*y+c)%n;g=math.gcd(abs(x-y),n)
  if g!=n:return min(smallest(g),smallest(n//g))
  c+=1
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i,n in enumerate(v[1:1+v[0]],1):
 answer=n//2-1 if n%2==0 else (n-smallest(n))//2
 out.append(f'Case #{i}: {answer}')
print('\n'.join(out))
