import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);red=[];blue=[];redmask=0
for i in range(n):
 c,r,b=v[1+3*i:4+3*i];red.append(int(r));blue.append(int(b))
 if c==b'R':redmask|=1<<i
size=1<<n;dp=[None]*size;dp[0]={0:0};full=size-1
for mask in range(full):
 states=dp[mask];nr=(mask&redmask).bit_count();nb=mask.bit_count()-nr;remaining=full^mask
 while remaining:
  bit=remaining&-remaining;remaining-=bit;i=bit.bit_length()-1;dr=min(red[i],nr);db=min(blue[i],nb);target=mask|bit
  if dp[target] is None:dp[target]={}
  dest=dp[target]
  for a,b in states.items():
   x=a+dr;y=b+db
   if y>dest.get(x,-1):dest[x]=y
 dp[mask]=None
sr=sum(red);sb=sum(blue)
print(n+min(max(sr-a,sb-b) for a,b in dp[full].items()))
