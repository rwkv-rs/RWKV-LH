import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];values=v[1:];M=max(values);spf=array('i',range(M+1));omega=bytearray(M+1)
for p in range(2,int(M**0.5)+1):
 if spf[p]==p:
  for x in range(p*p,M+1,p):
   if spf[x]==x:spf[x]=p
for x in range(2,M+1):omega[x]=omega[x//spf[x]]+1
positions={}
for i,x in enumerate(values,1):positions.setdefault(x,[]).append(i)
first=array('i',[0])*(M+1);second=array('i',[0])*(M+1);weights=[0]+[omega[x] for x in values]
def divisors(x):
 result=[1]
 while x>1:
  p=spf[x];power=1;old=result[:]
  while x%p==0:
   x//=p;power*=p;result += [d*power for d in old]
 return result
for x,ids in positions.items():
 for divisor in divisors(x):
  for i in ids[:2]:
   j=first[divisor]
   if not j or (weights[i],i)<(weights[j],j):second[divisor]=j;first[divisor]=i
   else:
    j=second[divisor]
    if not j or (weights[i],i)<(weights[j],j):second[divisor]=i
out=[0]*n
for x,ids in positions.items():
 if len(ids)>1:
  for i in ids:out[i-1]=ids[1] if i==ids[0] else ids[0]
  continue
 i=ids[0];best=(10**9,0)
 for divisor in divisors(x):
  j=first[divisor] if first[divisor]!=i else second[divisor]
  if j:best=min(best,(omega[x]+weights[j]-2*omega[divisor],j))
 out[i-1]=best[1]
print('\n'.join(map(str,out)))
