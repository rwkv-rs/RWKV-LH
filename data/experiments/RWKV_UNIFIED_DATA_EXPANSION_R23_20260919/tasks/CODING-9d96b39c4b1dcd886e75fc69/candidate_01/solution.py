import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for case in range(1,next(it)+1):
 n=next(it);parts=[]
 for a in range(2,math.isqrt(math.isqrt(n)+1)+1):
  factor=a*a-1
  if n%factor:continue
  value=n//factor+1;b=math.isqrt(value)
  if b*b==value and b>=a:parts.append(f'({a}^2-1)*({b}^2-1)')
 out.append(f'Case #{case}:')
 if parts:out.append(str(n)+'='+'='.join(parts))
 else:out.append(f'For n={n} there is no almost square factorisation.')
print('\n'.join(out))
