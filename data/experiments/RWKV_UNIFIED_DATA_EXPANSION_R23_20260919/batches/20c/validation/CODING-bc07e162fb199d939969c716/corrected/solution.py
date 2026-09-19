import sys
v=list(map(int,sys.stdin.read().split()));n,x,y=v[:3];a=v[3:3+n];b=v[3+n:3+2*n];size=1<<n;dp=[10**40]*size;dp[0]=0
for mask in range(size):
 pos=mask.bit_count()
 if pos==n:continue
 remaining=(size-1)^mask
 while remaining:
  bit=remaining&-remaining;remaining-=bit;i=bit.bit_length()-1;swaps=i-(mask&(bit-1)).bit_count();new=mask|bit
  cost=dp[mask]+swaps*y+abs(a[i]-b[pos])*x
  if cost<dp[new]:dp[new]=cost
print(dp[-1])
