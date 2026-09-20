import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=0;out=[]
while p<len(v):
 n,m=v[p:p+2];p+=2;deadlines=v[p:p+n];p+=n;rooms=[[] for _ in range(n)]
 for _ in range(m):r,value,time=v[p:p+3];p+=3;rooms[r].append((value,time))
 limit=10**30
 for i in range(n):limit=min(limit,deadlines[i]-1);deadlines[i]=limit
 dp=[0]
 for room in range(n-1,-1,-1):
  capacity=deadlines[room];dp.extend([dp[-1]]*(capacity+1-len(dp)))
  for value,time in rooms[room]:
   for used in range(time,capacity+1):
    candidate=dp[used-time]+value
    if candidate>dp[used]:dp[used]=candidate
 out.append(str(dp[-1]))
print('\n'.join(out))
