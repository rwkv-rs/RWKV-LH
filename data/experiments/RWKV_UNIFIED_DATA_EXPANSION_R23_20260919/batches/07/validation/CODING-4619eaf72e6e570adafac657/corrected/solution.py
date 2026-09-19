import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];answer=[0]*(n+1)
for left in range(n):
 counts=[0]*(n+1);best=0;frequency=0
 for right in range(left,n):
  color=a[right];counts[color]+=1;value=counts[color]
  if value>frequency or value==frequency and color<best:best=color;frequency=value
  answer[best]+=1
print(' '.join(map(str,answer[1:])))
