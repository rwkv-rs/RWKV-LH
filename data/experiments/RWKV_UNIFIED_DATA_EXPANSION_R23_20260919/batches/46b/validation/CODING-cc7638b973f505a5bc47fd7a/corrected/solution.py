import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 a,b,c,d=[next(it) for _ in range(4)];answer=0
 for y in range(1,(d*c-1)//b+1):
  denominator=d*c-b*y
  if a*c*y%denominator==0:answer+=1
 out.append(str(answer))
print('\n'.join(out))
