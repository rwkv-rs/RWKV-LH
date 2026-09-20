import sys
n,k=map(int,sys.stdin.buffer.read().split());MOD=998244353;base=(n+1)%MOD
if base==0:print(0);raise SystemExit
limit=min(n,k);fact=[1]*(limit+1)
for i in range(1,limit+1):fact[i]=fact[i-1]*i%MOD
inverse=[1]*(limit+1);inverse[limit]=pow(fact[limit],MOD-2,MOD)
for i in range(limit,0,-1):inverse[i-1]=inverse[i]*i%MOD
width=(( (limit+1)*(MOD-1)**2 ).bit_length()+7)//8
left=b''.join((pow(i,k,MOD)*inverse[i]%MOD).to_bytes(width,'little') for i in range(limit+1));right=b''.join((inverse[i] if i%2==0 else (MOD-inverse[i])%MOD).to_bytes(width,'little') for i in range(limit+1));product=int.from_bytes(left,'little')*int.from_bytes(right,'little');data=product.to_bytes(width*(2*limit+1),'little');answer=0;falling=1;power=pow(base,n,MOD);invbase=pow(base,MOD-2,MOD)
for j in range(1,limit+1):
 falling=falling*((n-j+1)%MOD)%MOD;power=power*invbase%MOD
 stirling=int.from_bytes(data[j*width:(j+1)*width],'little')%MOD
 answer=(answer+stirling*falling%MOD*power)%MOD
print(answer)
