import sys
v=sys.stdin.read().split();out=[]
for case in range(int(v[0])):
 s=sorted(v[1+2*case]);d=int(v[2+2*case]);n=len(s);digits=list(map(int,s));dp=[{} for _ in range(1<<n)];dp[0][0]=1
 for mask in range((1<<n)-1):
  for i,digit in enumerate(digits):
   if mask>>i&1 or i>0 and digit==digits[i-1] and not(mask>>(i-1)&1):continue
   target=dp[mask|1<<i]
   for remainder,ways in dp[mask].items():
    r=(10*remainder+digit)%d;target[r]=target.get(r,0)+ways
 out.append(str(dp[-1].get(0,0)))
print('\n'.join(out))
