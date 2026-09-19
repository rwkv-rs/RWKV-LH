import sys,math
n,k=map(int,sys.stdin.read().split());multiple=1;i=1
while i<=k:
 multiple=math.lcm(multiple,i)
 if multiple>n+1 or (n+1)%multiple:print('No');break
 i+=1
else:print('Yes')
