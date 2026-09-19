import sys
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);p=next(it);a=[next(it) for _ in range(n)];b=[next(it) for _ in range(n)];remaining=n-1;answer=p
 for cost,capacity in sorted(zip(b,a)):
  if cost>=p:break
  count=min(remaining,capacity);answer+=count*cost;remaining-=count
  if not remaining:break
 answer+=remaining*p;out.append(str(answer))
print('\n'.join(out))
