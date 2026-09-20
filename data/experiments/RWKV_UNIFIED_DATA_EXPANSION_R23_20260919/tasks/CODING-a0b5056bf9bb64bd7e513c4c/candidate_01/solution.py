import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for case in range(1,next(it)+1):
 n,t=next(it),next(it);songs=[next(it) for _ in range(n)];limit=min(t-1,sum(songs));dp=[-1]*(limit+1);dp[0]=0
 for length in songs:
  for time in range(limit,length-1,-1):
   if dp[time-length]>=0:dp[time]=max(dp[time],dp[time-length]+1)
 count,time=max((count,time) for time,count in enumerate(dp));out.append(f'Case {case}: {count+1} {time+678}')
print('\n'.join(out))
