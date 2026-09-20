import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,x=v[:2];a=v[2:];answer=x
for k in range(1,n+1):
 dp=[[-1]*k for _ in range(k+1)];dp[0][0]=0
 for seen,value in enumerate(a):
  for used in range(min(seen+1,k),0,-1):
   old,new=dp[used-1],dp[used]
   for residue,total in enumerate(old):
    if total>=0:
     candidate=total+value;r=(residue+value)%k
     if candidate>new[r]:new[r]=candidate
 best=dp[k][x%k]
 if best>=0:answer=min(answer,(x-best)//k)
print(answer)
