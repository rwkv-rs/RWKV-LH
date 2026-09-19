import sys
n,m,k=map(int,sys.stdin.read().split());mod=1000000007
if n>m+k:print(0);raise SystemExit
size=n+m;factorial=[1]*(size+1)
for i in range(1,size+1):factorial[i]=factorial[i-1]*i%mod
def choose(r):
 if r<0 or r>size:return 0
 return factorial[size]*pow(factorial[r]*factorial[size-r]%mod,mod-2,mod)%mod
print((choose(n)-choose(n-k-1))%mod)
