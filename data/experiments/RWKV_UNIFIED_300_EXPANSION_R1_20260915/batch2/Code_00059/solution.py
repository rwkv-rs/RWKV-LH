import sys
a=iter(map(int,sys.stdin.buffer.read().split()));n,t=next(a),next(a);food=sorted((next(a),next(a)) for _ in range(n));dp=[-10**20]*t;dp[0]=0;ans=0
for duration,value in food:
    ans=max(ans,max(dp)+value)
    for used in range(t-1,duration-1,-1):dp[used]=max(dp[used],dp[used-duration]+value)
print(ans)
