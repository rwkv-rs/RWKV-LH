import sys
a=list(map(int,sys.stdin.buffer.read().split()))[1:];dp=[0]*4;pat=[1,2,1,2]
for x in a:
 best=0;nd=[]
 for j in range(4):best=max(best,dp[j]);nd.append(best+(x==pat[j]))
 dp=nd
print(max(dp))
