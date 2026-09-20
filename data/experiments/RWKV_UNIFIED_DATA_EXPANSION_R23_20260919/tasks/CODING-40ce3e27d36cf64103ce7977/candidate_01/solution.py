import sys,math
v=iter(map(int,sys.stdin.buffer.read().split()));t=next(v);out=[];MOD=10000000
for _ in range(t):
 p=next(v);q=next(v);k=next(v);m=p+k
 if k==0 or p+q==0 or q>2*m:out.append('0');continue
 if m==1:ways=[1,2,1][q]
 else:
  gaps=m-1;ways=0
  for j in range(min(gaps,q//3)+1):
   degree=q-3*j;coefficient=math.comb(gaps+degree-1,degree)
   if degree>=1:coefficient+=2*math.comb(gaps+degree-2,degree-1)
   if degree>=2:coefficient+=math.comb(gaps+degree-3,degree-2)
   term=math.comb(gaps,j)*coefficient
   ways+=-term if j%2 else term
 out.append(str(ways*math.comb(m,k)%MOD))
print('\n'.join(out))
