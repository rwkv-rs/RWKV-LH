import sys
n,m,k=map(int,sys.stdin.read().split());mod=1000000007
bad=[0]*(n+1);bad[0]=1;power=1;good=0
for i in range(1,n+1):
 power=power*m%mod
 good=good*m%mod
 if i==k:good=(good+m)%mod
 elif i>k:good=(good+(m-1)*bad[i-k])%mod
 bad[i]=(power-good)%mod
print(good)
