import sys,math
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
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
 if n<1<<64:return True
 for p in range(41,math.isqrt(n)+1,2):
  if n%p==0:return False
 return True
def solve(n):
 length=len(str(n))
 while length:
  if length%2==0:
   if length==2 and n>=11:return 11
   length-=1;n=10**length-1;continue
  digits=(length+1)//2;prefix=int(str(n)[:digits]);minimum=10**(digits-1)
  while prefix>=minimum:
   s=str(prefix);value=int(s+s[-2::-1])
   if value<=n and prime(value):return value
   prefix-=1
  length-=2;n=10**max(0,length)-1
 return 2
v=list(map(int,sys.stdin.buffer.read().split()));print('\n'.join(str(solve(n)) for n in v[1:]))
