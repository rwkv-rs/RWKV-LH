import sys,math
v=list(map(int,sys.stdin.read().split()));n=v[0];p=[x-1 for x in v[1:n+1]];q=[x-1 for x in v[n+1:2*n+1]];cid=[-1]*n;pos=[0]*n;lengths=[]
for start in range(n):
 if cid[start]>=0:continue
 c=len(lengths);x=start;length=0
 while cid[x]<0:cid[x]=c;pos[x]=length;length+=1;x=q[x]
 lengths.append(length)
answer=0;modulus=1;ok=True
for i,x in enumerate(p):
 if cid[i]!=cid[x]:ok=False;break
 m=lengths[cid[i]];r=(pos[i]-pos[x])%m;g=math.gcd(modulus,m)
 if (r-answer)%g:ok=False;break
 reduced=m//g
 if reduced>1:answer+=modulus*((r-answer)//g*pow(modulus//g,-1,reduced)%reduced)
 modulus*=reduced;answer%=modulus
print(answer if ok else -1)
