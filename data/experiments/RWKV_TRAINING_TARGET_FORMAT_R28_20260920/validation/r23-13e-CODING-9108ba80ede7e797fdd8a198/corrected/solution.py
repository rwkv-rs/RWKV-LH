import sys
v=sys.stdin.read().split();cases=int(v[0]);at=1;out=[]
for case in range(1,cases+1):
 n,k,m=map(int,v[at:at+3]);at+=3;prob=list(map(float,v[at:at+n]));at+=n;extinct=0.0
 for _ in range(m):
  new=0.0
  for p in reversed(prob):new=new*extinct+p
  extinct=new
 out.append('Case #'+str(case)+': '+format(extinct**k,'.7f'))
print('\n'.join(out))
