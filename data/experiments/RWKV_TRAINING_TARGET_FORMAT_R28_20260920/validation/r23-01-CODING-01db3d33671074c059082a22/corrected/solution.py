import sys
s,k=sys.stdin.buffer.read().split();k=int(k);mod=1000000007;dp=[0]*(k+1);mask=0
for i,c in enumerate(s):
 d=c-48 if c<=57 else c-55;nd=[0]*(k+1)
 for j in range(1,k+1):nd[j]=(dp[j]*j+dp[j-1]*(17-j))%mod
 if i:nd[1]=(nd[1]+15)%mod
 for v in range(0 if i else 1,d):
  count=(mask|(1<<v)).bit_count()
  if count<=k:nd[count]=(nd[count]+1)%mod
 mask|=1<<d;dp=nd
print((dp[k]+(mask.bit_count()==k))%mod)
