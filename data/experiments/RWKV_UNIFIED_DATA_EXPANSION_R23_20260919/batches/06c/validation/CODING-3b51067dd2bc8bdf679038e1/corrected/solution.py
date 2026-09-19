import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
while True:
 try:m=next(it);n=next(it)
 except StopIteration:break
 if m==n==0:break
 dp=[1]+[0]*n
 for _ in range(m):
  low=next(it);high=next(it);new=[0]*(n+1);window=0
  for total in range(n+1):
   if total>=low:window+=dp[total-low]
   if total>high:window-=dp[total-high-1]
   new[total]=window
  dp=new
 out.append(str(dp[n]))
print('\n'.join(out))
