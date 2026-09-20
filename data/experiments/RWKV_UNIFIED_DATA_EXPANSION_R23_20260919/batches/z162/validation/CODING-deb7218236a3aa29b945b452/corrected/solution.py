import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];MOD=998244353;inverse=[0]*(n+1);inverse[1]=1
for i in range(2,n+1):inverse[i]=MOD-(MOD//i)*inverse[MOD%i]%MOD
schroeder=[0]*(max(2,n-1));schroeder[0]=1;schroeder[1]=2
for i in range(2,n-1):schroeder[i]=(3*(2*i-1)*schroeder[i-1]-(i-2)*schroeder[i-2])*inverse[i+1]%MOD
graphs=[0]*(n+1);power=2
for i in range(2,n+1):graphs[i]=power*schroeder[i-2]%MOD;power=power*2%MOD
width=max(1,((n*max(a,default=0)**2).bit_length()+7)//8);left=int.from_bytes(b''.join(x.to_bytes(width,'little') for x in a),'little');right=int.from_bytes(b''.join(x.to_bytes(width,'little') for x in reversed(a)),'little');data=(left*right).to_bytes((2*n-1)*width,'little');answer=0
for d in range(1,n):
 coefficient=n-1-d;correlation=int.from_bytes(data[coefficient*width:(coefficient+1)*width],'little')%MOD
 answer=(answer+correlation*graphs[d+1]%MOD*graphs[n-d+1])%MOD
print(answer*pow(4*graphs[n]%MOD,MOD-2,MOD)%MOD)
