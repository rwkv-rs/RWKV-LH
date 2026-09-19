import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));queries=[tuple(v[1+2*i:3+2*i]) for i in range(v[0])];limit=max((r for l,r in queries),default=1);prime=bytearray(b'\x01')*(limit+1)
for i in range(min(2,limit+1)):prime[i]=0
for p in range(2,math.isqrt(limit)+1):
 if prime[p]:prime[p*p::p]=b'\x00'*((limit-p*p)//p+1)
valid=[]
for x in range(1,limit+1):
 ok=True
 for d in range(2,math.isqrt(x)+1):
  if x%d==0 and (not prime[d] or not prime[x//d]):ok=False;break
 if ok:valid.append(x)
out=[]
for l,r in queries:
 values=[str(x) for x in valid if l<=x<=r];out.append(' '.join(values) if values else '-1')
print('\n'.join(out))
