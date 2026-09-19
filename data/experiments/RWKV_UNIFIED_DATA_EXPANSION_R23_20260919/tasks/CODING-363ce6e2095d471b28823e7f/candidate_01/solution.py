import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];reach=[{} for _ in range(n)];dp=[0]*(n+1)
for i in range(n-1,-1,-1):
 value=a[i];end=i+1;reach[i][value]=end;dp[i]=1+dp[end]
 while end<n and value in reach[end]:
  end=reach[end][value];value+=1;reach[i][value]=end;dp[i]=min(dp[i],1+dp[end])
print(dp[0])
