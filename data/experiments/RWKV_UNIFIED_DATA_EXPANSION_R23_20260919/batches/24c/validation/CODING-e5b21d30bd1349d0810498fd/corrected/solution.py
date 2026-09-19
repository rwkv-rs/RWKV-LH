import sys
v=list(map(int,sys.stdin.read().split()));n,m=v[:2];weights=v[2:2+n];dp=[0]*(m+1);dp[0]=1
for w in weights:
 for x in range(m,w-1,-1):dp[x]=(dp[x]+dp[x-w])%10
out=[]
for w in weights:
 remaining=dp.copy()
 for x in range(w,m+1):remaining[x]=(dp[x]-remaining[x-w])%10
 out.append(''.join(map(str,remaining[1:])))
print('\n'.join(out))
