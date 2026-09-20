import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[];case=0
for n in it:
 if n==0:break
 neighborhoods=[]
 for i in range(n):
  m=next(it);mask=1<<i
  for _ in range(m):mask|=1<<next(it)
  neighborhoods.append(mask)
 full=(1<<n)-1;cover=[0]*(1<<n)
 for mask in range(1,1<<n):bit=mask&-mask;cover[mask]=cover[mask^bit]|neighborhoods[bit.bit_length()-1]
 dp=bytearray(1<<n)
 for mask in range(1,1<<n):
  if cover[mask]!=full:continue
  best=1;anchor=mask&-mask;rest=mask^anchor;sub=rest
  while sub:
   group=sub|anchor
   if cover[group]==full:best=max(best,1+dp[mask^group])
   sub=(sub-1)&rest
  if cover[anchor]==full:best=max(best,1+dp[rest])
  dp[mask]=best
 case+=1;out.append(f'Case {case}: {dp[full]}')
print('\n'.join(out))
