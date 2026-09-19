import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,left,right=v[:3];dp=[1]+[0]*right
for weight in v[3:3+n]:
 for total in range(right,weight-1,-1):dp[total]+=dp[total-weight]
print(sum(dp[left:right+1]))
