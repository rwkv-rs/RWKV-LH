import sys
from array import array
values=[]
for x in map(int,sys.stdin.buffer.read().split()):
 if x==0:break
 values.append(x)
limit=max(values,default=1);phi=array('I',range(limit+1))
for p in range(2,limit+1):
 if phi[p]==p:
  for j in range(p,limit+1,p):phi[j]-=phi[j]//p
prefix=array('Q',[0])*(limit+1);total=0
for i in range(2,limit+1):total+=phi[i];prefix[i]=total
print('\n'.join(str(prefix[x]) for x in values))
