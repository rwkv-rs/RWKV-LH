import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 length,multiplier=next(it),next(it);best=None
 for last in range(1,10):
  digits=[last];carry=0
  for i in range(length-1):value=digits[-1]*multiplier+carry;digits.append(value%10);carry=value//10
  if digits[-1] and digits[-1]*multiplier+carry==last:
   candidate=''.join(map(str,reversed(digits)))
   if best is None or candidate<best:best=candidate
 out.append(best if best is not None else 'Impossible')
print('\n'.join(out))
