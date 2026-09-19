import sys,bisect,math
qs=[]
for x in map(int,sys.stdin.read().split()):
 if x==0:break
 qs.append(x)
if qs:
 limit=1024
 while True:
  phi=list(range(limit+1))
  for p in range(2,limit+1):
   if phi[p]==p:
    for j in range(p,limit+1,p):phi[j]-=phi[j]//p
  sums=[0]*(limit+1);sums[1]=2
  for i in range(2,limit+1):sums[i]=sums[i-1]+phi[i]
  if sums[-1]>=max(qs):break
  limit*=2
 out=[]
 for k in qs:
  if k<=2:out.append(str(k-1)+'/1');continue
  d=bisect.bisect_left(sums,k);rank=k-sums[d-1]
  for a in range(1,d):
   if math.gcd(a,d)==1:
    rank-=1
    if not rank:out.append(str(a)+'/'+str(d));break
 print('\n'.join(out))
