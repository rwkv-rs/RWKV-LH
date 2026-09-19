import sys
lines=iter(sys.stdin.read().splitlines());t=int(next(lines));groups=[];current=[]
for line in lines:
 if line.strip():current.append(line)
 elif current:groups.append(current);current=[]
if current:groups.append(current)
out=[];inf=10**30
for block in groups[:t]:
 destination=int(block[0]);stations=sorted(tuple(map(int,line.split())) for line in block[1:]);dp=[inf]*201;dp[100]=0;previous=0
 for position,price in stations:
  if position>destination:break
  distance=position-previous
  dp=dp[distance:]+[inf]*min(distance,201) if distance<=200 else [inf]*201
  for fuel in range(1,201):dp[fuel]=min(dp[fuel],dp[fuel-1]+price)
  previous=position
 need=destination-previous+100;answer=min(dp[need:],default=inf)
 out.append(str(answer) if answer<inf else 'Impossible')
print('\n\n'.join(out))
