import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,initial,target=v[:3]
if initial>=target:print(0);raise SystemExit
best={}
for price,rate in zip(v[3::2],v[4::2]):
 if price<target:best[price]=max(best.get(price,0),min(rate,target))
peons=[];maximum=-1
for price,rate in sorted(best.items()):
 if rate>maximum:peons.append((price,rate));maximum=rate
dp=[-1]*target;dp[initial]=0;elapsed=0
while True:
 for money in range(target-1,-1,-1):
  rate=dp[money]
  if rate<0:continue
  for price,gain in peons:
   if price>money:break
   remaining=money-price;newrate=min(target,rate+gain)
   if newrate>dp[remaining]:dp[remaining]=newrate
 nextdp=[-1]*target;elapsed+=1
 for money,rate in enumerate(dp):
  if rate<0:continue
  after=money+rate
  if after>=target:print(elapsed);raise SystemExit
  if rate>nextdp[after]:nextdp[after]=rate
 dp=nextdp
