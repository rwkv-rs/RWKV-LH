import sys,bisect
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));m,q=v[:2];primes=sorted(set(v[2:2+m]));queries=v[2+m:];limit=max(queries)
if primes[-1]>limit:print('\n'.join('1' for _ in queries));raise SystemExit
largest=array('i',[0])*(limit+1)
for p in primes:
 for x in range(p,limit+1,p):largest[x]=p
frontiers=[0];reach=primes[-1]-1;scanned=0
while reach>frontiers[-1]:
 frontiers.append(min(reach,limit))
 if reach>=limit:break
 old=reach
 while scanned<=old:
  reach=max(reach,scanned+largest[scanned]-1);scanned+=1
print('\n'.join(str(bisect.bisect_left(frontiers,n)) if n<=frontiers[-1] else 'oo' for n in queries))
