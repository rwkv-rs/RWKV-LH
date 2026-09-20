import sys
from array import array
v=sys.stdin.buffer.read().split();n,k=map(int,v[:2]);s=v[2];MOD=1000000007
if 2*k>n:print(0);raise SystemExit
def avoid(text,letter):
 f=array('i',[0])*(n+1);first=array('i',[0])*(n+1);f[0]=1;streak=0
 for i,ch in enumerate(text,1):
  allowed=ch in (letter,88);streak=streak+1 if allowed else 0;new=0
  if streak>=k:
   if i==k:new=1
   elif text[i-k-1]!=letter:new=f[i-k-1]
  first[i]=new;f[i]=((2 if ch==88 else 1)*f[i-1]-new)%MOD
 return f,first
_,first=avoid(s,66);reverse=s[::-1];white,_=avoid(reverse,87);total=array('i',[1])*(n+1)
for i,ch in enumerate(reverse,1):total[i]=total[i-1]*(2 if ch==88 else 1)%MOD
print(sum(first[i]*(total[n-i]-white[n-i]) for i in range(k,n-k+1))%MOD)
