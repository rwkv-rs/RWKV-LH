import sys,bisect
v=iter(map(int,sys.stdin.buffer.read().split()));t=next(v);fib=[1,2]
while fib[-1]<=10**18:fib.append(fib[-1]+fib[-2])
out=[]
for _ in range(t):
 k,n=next(v),next(v);remaining=n-1;cut=bisect.bisect_right(fib,k);losing=0;valid=True
 for i in range(len(fib)-1,-1,-1):
  if fib[i]<=remaining:
   losing+=fib[max(0,i-cut)]
   if i<cut:valid=False;break
   remaining-=fib[i]
 if valid:losing+=1
 out.append(str(n-losing))
print('\n'.join(out))
