import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];antennas=[(x-s,x+s) for x,s in zip(v[2::2],v[3::2])];dp=[10**30]*(m+1);dp[0]=0
for covered in range(m):
 value=dp[covered];nextpoint=covered+1
 if covered and value+1<dp[nextpoint]:dp[nextpoint]=value+1
 for left,right in antennas:
  extra=max(0,left-nextpoint,nextpoint-right);end=min(m,right+extra);candidate=value+extra
  if candidate<dp[end]:dp[end]=candidate
print(dp[m])
