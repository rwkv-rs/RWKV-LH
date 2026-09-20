import sys
v=list(map(int,sys.stdin.buffer.read().split()));pairs=[]
for a,b in zip(v[::2],v[1::2]):
 if a==b==0:break
 pairs.append((a,b))
limit=max((min(a,b) for a,b in pairs),default=0);mu=[1]*(limit+1);prime=[True]*(limit+1)
for p in range(2,limit+1):
 if prime[p]:
  for j in range(p,limit+1,p):mu[j]=-mu[j];prime[j]=False
  for j in range(p*p,limit+1,p*p):mu[j]=0
out=[]
for a,b in pairs:
 visible=4*sum(mu[d]*(a//d)*(b//d) for d in range(1,min(a,b)+1))+2*(a>0)+2*(b>0)
 total=(2*a+1)*(2*b+1)-1;out.append(f'{visible/total:.7f}')
print('\n'.join(out))
