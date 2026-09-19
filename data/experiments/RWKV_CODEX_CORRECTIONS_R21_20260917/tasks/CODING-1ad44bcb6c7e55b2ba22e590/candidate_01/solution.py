import sys,bisect
it=iter(map(int,sys.stdin.buffer.read().split()));t=next(it);out=[]
for _ in range(t):
 n=next(it);orders=[]
 for _ in range(n):
  start=next(it);duration=next(it);price=next(it);orders.append((start+duration,start,price))
 orders.sort();ends=[];dp=[0]
 for end,start,price in orders:
  earlier=bisect.bisect_right(ends,start);dp.append(max(dp[-1],dp[earlier]+price));ends.append(end)
 out.append(str(dp[-1]))
print('\n'.join(out))
