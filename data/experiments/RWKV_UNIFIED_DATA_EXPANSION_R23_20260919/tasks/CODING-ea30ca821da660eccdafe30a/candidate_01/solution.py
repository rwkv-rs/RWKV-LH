import sys
n,d=map(int,sys.stdin.read().split());mod=998244353;power=1;desc=pow(2,d,mod);cross=pow(2,d-2,mod) if d>=2 else 0;answer=0
for depth in range(n):
 h=n-1-depth;ways=desc if d<=h else 0
 if d>=2:ways+=max(0,min(h,d-1)-max(1,d-h)+1)*cross
 answer=(answer+power*ways)%mod;power=power*2%mod
print(answer*2%mod)
