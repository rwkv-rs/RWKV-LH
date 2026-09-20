import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:1+n];b=v[1+n:1+2*n];answer=0;previous=0
for x,y in zip(a,b):
 current=y-x
 if current*previous<=0:answer+=abs(current)
 else:answer+=max(0,abs(current)-abs(previous))
 previous=current
print(answer)
