import sys,math
n,k=map(int,sys.stdin.buffer.read().split());MOD=1000000007
if k>n//2:print(0);raise SystemExit
inverse2=(MOD+1)//2;dp=[None]*(n+1);dp[1]={(0,1):1}
for size in range(2,n+1):
 result={}
 for (matches,free),ways in dp[size-1].items():
  key=(matches+free,1-free)
  if key[0]<=k:result[key]=(result.get(key,0)+(size-1)*ways)%MOD
 for a in range(1,size-1):
  b=size-1-a;factor=math.comb(size-1,a)*a*b*inverse2%MOD
  for (ma,fa),wa in dp[a].items():
   for (mb,fb),wb in dp[b].items():
    extra=int(fa or fb);key=(ma+mb+extra,1-extra)
    if key[0]<=k:result[key]=(result.get(key,0)+factor*wa*wb)%MOD
 dp[size]=result
print(sum(ways for (matches,free),ways in dp[n].items() if matches==k)%MOD)
