import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));cases=next(it);out=[]
for _ in range(cases):
 n=next(it);k=next(it);d=[next(it) for _ in range(n)];lo=0;hi=min(d)*k+k*(k-1)//2
 while lo<hi:
  mid=(lo+hi)//2;count=0
  for x in d:
   b=2*x-1;count+=(math.isqrt(b*b+8*mid)-b)//2
   if count>=k:break
  if count>=k:hi=mid
  else:lo=mid+1
 out.append(str(lo))
print('\n'.join(out))
