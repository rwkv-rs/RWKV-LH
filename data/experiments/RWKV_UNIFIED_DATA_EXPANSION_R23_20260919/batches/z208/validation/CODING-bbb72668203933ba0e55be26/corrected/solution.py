import sys
P=10007
fac=[1]*P
for i in range(1,P):fac[i]=fac[i-1]*i%P
inv=[1]*P;inv[-1]=pow(fac[-1],P-2,P)
for i in range(P-1,0,-1):inv[i-1]=inv[i]*i%P
def choose(n,k):
 value=1
 while n or k:
  a=n%P;b=k%P
  if b>a:return 0
  value=value*fac[a]*inv[b]*inv[a-b]%P;n//=P;k//=P
 return value
def solve(ms,c):
 limit=min(ms)-1
 if c>limit+1:return 0
 h=[0]+[choose(g-1,c-2) for g in range(1,limit+1)]
 for k in range(1,limit+1):
  x=h[k]
  if x:
   for multiple in range(k+k,limit+1,k):h[multiple]=(h[multiple]-x)%P
 answer=0
 for k in range(1,limit+1):
  value=h[k]
  if value:
   for m in ms:
    q=(m-1)//k;value=value*(q*m-k*q*(q+1)//2)%P
   answer+=value
 return answer%P
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);c=next(v);out.append(str(solve([next(v) for _ in range(n)],c)))
print('\n'.join(out))
