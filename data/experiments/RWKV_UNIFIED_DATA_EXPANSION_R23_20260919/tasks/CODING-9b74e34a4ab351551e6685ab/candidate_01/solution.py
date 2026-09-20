import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];A=v[1:n+1];B=v[n+1:];limit=1<<n;dp=bytearray([255])*(limit*n)
for i in range(n):dp[(1<<i)*n+i]=i
for mask in range(1,limit):
 length=mask.bit_count();best=[255]*51;base=mask*n;bits=mask
 while bits:
  bit=bits&-bits;i=bit.bit_length()-1;value=A[i] if (i-length+1)%2==0 else B[i];best[value]=min(best[value],dp[base+i]);bits^=bit
 for i in range(1,51):best[i]=min(best[i],best[i-1])
 bits=(limit-1)^mask
 while bits:
  bit=bits&-bits;i=bit.bit_length()-1;value=A[i] if (i-length)%2==0 else B[i];cost=best[value]+(i-(mask&((1<<i)-1)).bit_count());p=(mask|bit)*n+i
  if cost<dp[p]:dp[p]=cost
  bits^=bit
answer=min(dp[(limit-1)*n:]);print(answer if answer<255 else -1)
