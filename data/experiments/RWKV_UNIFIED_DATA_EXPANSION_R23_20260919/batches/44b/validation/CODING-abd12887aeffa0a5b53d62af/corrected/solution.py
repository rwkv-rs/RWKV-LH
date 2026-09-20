import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,d=v[:2];a=v[2:];bits=1
for x in a:bits|=bits<<x
limit=sum(a);raw=bits.to_bytes((limit+8)//8,'little');previous=[0]*(limit+1);best=0
for i in range(limit+1):
 if raw[i>>3]>>(i&7)&1:best=i
 previous[i]=best
value=days=0
while True:
 nxt=previous[min(limit,value+d)]
 if nxt==value:break
 value=nxt;days+=1
print(value,days)
