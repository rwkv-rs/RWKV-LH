import sys,math
n,m=map(int,sys.stdin.read().split());pairs=[]
for length in range(1,math.isqrt(2*m)+1):
 if 2*m%length:continue
 twice_start=2*m//length-length+1
 if twice_start>0 and twice_start%2==0:
  start=twice_start//2;end=start+length-1
  if end<=n:pairs.append((start,end))
print('\n'.join('['+str(a)+','+str(b)+']' for a,b in sorted(pairs)))
