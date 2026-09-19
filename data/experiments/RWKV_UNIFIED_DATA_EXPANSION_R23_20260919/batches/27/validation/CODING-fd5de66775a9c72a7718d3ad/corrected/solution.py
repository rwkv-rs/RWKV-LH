import sys
n,m=map(int,sys.stdin.read().split());mod=998244353
if n==2:print(0)
else:
 r=n-1;numerator=denominator=1
 for i in range(1,r+1):numerator=numerator*(m-i+1)%mod;denominator=denominator*i%mod
 print(numerator*pow(denominator,mod-2,mod)%mod*(n-2)%mod*pow(2,n-3,mod)%mod)
