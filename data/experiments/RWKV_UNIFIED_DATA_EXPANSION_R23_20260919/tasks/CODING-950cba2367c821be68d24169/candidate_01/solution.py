import sys,math,bisect
v=list(map(int,sys.stdin.buffer.read().split()));values=v[1:];maximum=max(values);powers=set();primes=[p for p in range(3,61,2) if all(p%d for d in range(2,math.isqrt(p)+1))]
for p in primes:
 base=2
 while True:
  value=base**p
  if value>maximum:break
  if math.isqrt(base)**2!=base:powers.add(value)
  base+=1
powers=sorted(powers)
print('\n'.join(str(n-math.isqrt(n)-bisect.bisect_right(powers,n)) for n in values))
