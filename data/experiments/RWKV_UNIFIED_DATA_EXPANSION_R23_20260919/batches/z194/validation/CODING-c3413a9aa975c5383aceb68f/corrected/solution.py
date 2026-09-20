import sys
P=1000000007
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);k=next(v);s=next(v);points=sorted((next(v)-1,next(v)-1) for _ in range(k));limit=(s-1).bit_length()
if limit==0:print(1);raise SystemExit
maximum=n+m-2;fac=[1]*(maximum+1)
for i in range(1,maximum+1):fac[i]=fac[i-1]*i%P
inv=[1]*(maximum+1);inv[-1]=pow(fac[-1],P-2,P)
for i in range(maximum,0,-1):inv[i-1]=inv[i]*i%P
# Coefficients accumulated from at most 2000 terms are below 2^72.
mask=(1<<72)-1;prior=[]
for x,y in points:
 packed=fac[x+y]*inv[x]%P*inv[y]%P
 for a,b,poly in prior:
  if b<=y:
   dx=x-a;dy=y-b;ways=fac[dx+dy]*inv[dx]%P*inv[dy]%P;packed+=poly*ways
 coefficients=[];previous=0
 for degree in range(limit):
  current=(packed&mask)%P;packed>>=72;coefficients.append((previous-current)%P);previous=current
 poly=int.from_bytes(b''.join(value.to_bytes(9,'little') for value in coefficients),'little');prior.append((x,y,poly))
x=n-1;y=m-1;total=fac[x+y]*inv[x]%P*inv[y]%P;packed=total
for a,b,poly in prior:
 dx=x-a;dy=y-b;ways=fac[dx+dy]*inv[dx]%P*inv[dy]%P;packed+=poly*ways
weighted=0
for degree in range(limit):
 count=(packed&mask)%P;packed>>=72;weighted+=( ((s+(1<<degree)-1)>>degree)-1)*count
print((1+weighted%P*pow(total,P-2,P))%P)
