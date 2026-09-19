import sys
x=int(sys.stdin.buffer.read());black=[i for i in range(16) if x>>(15-i)&1];targets=list(range(8,16));dp=[1000]*256;dp[0]=0
for mask in range(255):
 i=mask.bit_count();source=black[i]
 for j,target in enumerate(targets):
  if not(mask>>j&1):
   nxt=mask|1<<j;cost=dp[mask]+abs(source//4-target//4)+abs(source%4-target%4)
   if cost<dp[nxt]:dp[nxt]=cost
print(dp[255])
