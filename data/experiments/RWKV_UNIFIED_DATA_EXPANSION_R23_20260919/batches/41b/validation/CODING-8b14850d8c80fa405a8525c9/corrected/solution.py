import sys
n,h=map(int,sys.stdin.buffer.read().split())
def capacity(length):
 rising=max(0,min(length,(length-h+2)//2));falling=length-rising
 return rising*h+rising*(rising-1)//2+falling*(falling+1)//2
lo,hi=1,n
while lo<hi:
 mid=(lo+hi)//2
 if capacity(mid)>=n:hi=mid
 else:lo=mid+1
print(lo)
