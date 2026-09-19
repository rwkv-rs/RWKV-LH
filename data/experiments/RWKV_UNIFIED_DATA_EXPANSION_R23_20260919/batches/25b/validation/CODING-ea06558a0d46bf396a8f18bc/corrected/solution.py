import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 k=next(v);mod=next(v);values=[next(v) for i in range(k)];poly=[1];a,b=1,2
 for i in range(k):
  root=a;new=[0]*(len(poly)+1)
  for j,c in enumerate(poly):new[j]=(new[j]-root*c)%mod;new[j+1]=(new[j+1]+c)%mod
  poly=new;a,b=b,(a+b)%mod
 out.append(str(-sum(poly[j]*values[j] for j in range(k))%mod))
print('\n'.join(out))
