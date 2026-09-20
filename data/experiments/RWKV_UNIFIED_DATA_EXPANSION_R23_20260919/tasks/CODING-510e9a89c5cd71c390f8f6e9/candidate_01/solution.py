import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=1;out=[]
for _ in range(v[0]):
 n,m,mod=v[p:p+3];p+=3;s=v[p:p+m];p+=m
 if s[0]!=1 or any(b%a for a,b in zip(s,s[1:])):out.append('0');continue
 numerator=1;denominator=n
 for a,b in zip(s,s[1:]):
  ratio=b//a;primes=[];d=2
  while d*d<=ratio:
   if ratio%d==0:
    primes.append(d)
    while ratio%d==0:ratio//=d
   d+=1 if d==2 else 2
  if ratio>1:primes.append(ratio)
  terms=[(1,1)]
  for prime in primes:terms.extend([(product*prime,-sign) for product,sign in terms[:]])
  count=sum(sign*((n//a)//product) for product,sign in terms);numerator=numerator*count%mod;denominator=denominator*(n-n//b)%mod
 out.append(str(numerator*pow(denominator,mod-2,mod)%mod))
print('\n'.join(out))
