import sys
v=list(map(int,sys.stdin.buffer.read().split()));mod=1000000007;out=[]
for n,l in zip(v[::2],v[1::2]):
 if n==l==0:break
 out.append(str(l%mod if n==1 else (pow(n,l+1,mod)-n)*pow(n-1,mod-2,mod)%mod))
print('\n'.join(out))
