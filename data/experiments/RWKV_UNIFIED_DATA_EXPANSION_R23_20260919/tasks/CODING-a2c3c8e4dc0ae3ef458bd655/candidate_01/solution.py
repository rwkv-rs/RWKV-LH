import sys
v=iter(map(int,sys.stdin.buffer.read().split()));n,r,q=next(v),next(v),next(v);mod=1000000007;prefix=[0]*(n+1);inv=[1]*(n+1);inverse=pow(r,mod-2,mod);power=1
for i in range(1,n+1):power=power*r%mod;prefix[i]=(prefix[i-1]+power)%mod;inv[i]=inv[i-1]*inverse%mod
first=[0]*(n+2);second=[0]*(n+2)
def event(i,a,b):
 while i<=n:first[i]=(first[i]+a)%mod;second[i]=(second[i]+b)%mod;i+=i&-i
def total(x):
 i=x;a=b=0
 while i:a+=first[i];b+=second[i];i-=i&-i
 return (prefix[x]*a+b)%mod
def update(l,r,start):
 coefficient=start*inv[l]%mod;event(l,coefficient,-coefficient*prefix[l-1]);event(r+1,-coefficient,coefficient*prefix[r])
out=[]
for _ in range(q):
 kind=next(v)
 if kind==0:start,l,r=next(v),next(v),next(v);update(l,r,start)
 elif kind==1:l,r=next(v),next(v);out.append(str((total(r)-total(l-1))%mod))
 else:i=next(v);current=(total(i)-total(i-1))%mod;update(i,i,-current)
print('\n'.join(out))
