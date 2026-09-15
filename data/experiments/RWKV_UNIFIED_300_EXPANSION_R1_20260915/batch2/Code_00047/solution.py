import sys
a=list(map(int,sys.stdin.buffer.read().split()));n,k=a[:2];h=[0]+a[2:];inf=10**30
# Keeping n-k original columns is sufficient; changed gaps can be made monotone.
keep=n-k
if keep==0:print(0);raise SystemExit
dp=[0]+[inf]*n
for count in range(1,keep+1):
    nd=[inf]*(n+1)
    for i in range(count,n+1):
        best=inf
        for j in range(count-1,i):
            value=dp[j]+max(0,h[i]-h[j])
            if value<best:best=value
        nd[i]=best
    dp=nd
print(min(dp))
