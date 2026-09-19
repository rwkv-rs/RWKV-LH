import sys,math
v=list(map(int,sys.stdin.read().split()));out=[]
for k in v[1:1+v[0]]:
 k=abs(k);n=max(1,(math.isqrt(1+8*k)-1)//2)
 while n*(n+1)//2<k or (n*(n+1)//2-k)%2:n+=1
 out.append(str(n))
print('\n'.join(out))
