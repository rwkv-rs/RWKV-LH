import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[];prime=1000000007;exponent_mod=prime-1
for _ in range(next(it)):
 n=next(it);k=next(it);a=sorted(next(it) for _ in range(n));r=k-1;choose=[0]*n;value=1
 for i in range(r,n):
  if i>r:value=value*i//(i-r)
  choose[i]=value%exponent_mod
 total=choose[n-1];answer=1
 for i,x in enumerate(a):answer=answer*pow(x,(total-choose[i]-choose[n-1-i])%exponent_mod,prime)%prime
 out.append(str(answer))
print('\n'.join(out))
