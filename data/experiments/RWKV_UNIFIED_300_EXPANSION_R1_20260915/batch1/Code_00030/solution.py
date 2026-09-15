n,k=map(int,input().split());mod=10**9+7
if k%2:print(0);raise SystemExit
dp={(0,0):1}
for i in range(n):
    nd={}
    for (j,cost),v in dp.items():
        for h,mul in ((j+1,1),(j,2*j+1),(j-1,j*j)):
            c=cost+2*h
            if h<0 or h>n-i-1 or c>k:continue
            nd[h,c]=(nd.get((h,c),0)+v*mul)%mod
    dp=nd
print(dp.get((0,k),0))
