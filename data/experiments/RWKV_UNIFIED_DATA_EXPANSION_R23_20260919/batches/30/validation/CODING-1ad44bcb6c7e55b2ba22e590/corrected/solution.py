import sys,bisect
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);orders=[]
 for i in range(n):
  start=next(v);duration=next(v);price=next(v);orders.append((start+duration,start,price))
 orders.sort();ends=[end for end,start,price in orders];dp=[0]
 for i,(end,start,price) in enumerate(orders):dp.append(max(dp[-1],price+dp[bisect.bisect_right(ends,start,0,i)]))
 out.append(str(dp[-1]))
print('\n'.join(out))
