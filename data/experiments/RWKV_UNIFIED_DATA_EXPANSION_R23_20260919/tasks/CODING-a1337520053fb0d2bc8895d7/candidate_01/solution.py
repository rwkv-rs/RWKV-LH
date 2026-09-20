import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));it=iter(v);t=next(it);cases=[];maximum=1
for _ in range(t):
 n=next(it);a=[next(it) for i in range(n)];cases.append(a);maximum=max(maximum,max(a))
spf=list(range(maximum+1))
for p in range(2,math.isqrt(maximum)+1):
 if spf[p]==p:
  for j in range(p*p,maximum+1,p):
   if spf[j]==j:spf[j]=p
cache={1:(1,)};out=[]
for a in cases:
 count={};answer=0
 for x in a:
  answer=max(answer,count.get(x,0))
  if x not in cache:
   divisors=[1];value=x
   while value>1:
    p=spf[value];power=1;old=divisors.copy()
    while value%p==0:
     value//=p;power*=p;divisors.extend(d*power for d in old)
   cache[x]=tuple(divisors)
  for d in cache[x]:count[d]=count.get(d,0)+1
 out.append(str(answer))
print('\n'.join(out))
