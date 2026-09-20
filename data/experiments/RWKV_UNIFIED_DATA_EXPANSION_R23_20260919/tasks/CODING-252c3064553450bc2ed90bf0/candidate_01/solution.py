import sys
from bisect import bisect_right
a=list(map(int,sys.stdin.buffer.read().split()))[1:];maximum=max(a);present=bytearray(maximum+1)
for x in a:present[x]=1
spf=list(range(maximum+1))
for i in range(2,int(maximum**0.5)+1):
 if spf[i]==i:
  for j in range(i*i,maximum+1,i):
   if spf[j]==j:spf[j]=i
answer=maximum
for common in range(1,maximum+1):
 if maximum*maximum//common<=answer:break
 numbers=[x//common for x in range((maximum//common)*common,0,-common) if present[x]]
 if len(numbers)<2:continue
 positions={}
 for index,x in enumerate(numbers):
  if common*x*numbers[0]<=answer:break
  factors=[];v=x
  while v>1:
   p=spf[v];factors.append(p)
   while v%p==0:v//=p
  terms=[(1,1)]
  for p in factors:terms += [(d*p,-sign) for d,sign in terms]
  coprime=sum(sign*len(positions.get(d,())) for d,sign in terms)
  if coprime:
   lo=0;hi=index-1
   while lo<hi:
    mid=(lo+hi)//2;count=sum(sign*bisect_right(positions.get(d,()),mid) for d,sign in terms)
    if count:hi=mid
    else:lo=mid+1
   answer=max(answer,common*x*numbers[lo])
  for d,sign in terms:positions.setdefault(d,[]).append(index)
print(answer)
