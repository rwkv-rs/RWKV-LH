import sys
v=iter(map(int,sys.stdin.buffer.read().split()));t=next(v);cache={1:[0]};out=[]
for _ in range(t):
 a=next(v);b=next(v);n=next(v)
 if n not in cache:
  seq=[];x,y=0,1
  while True:
   seq.append(x);x,y=y,(x+y)%n
   if x==0 and y==1:break
  cache[n]=seq
 seq=cache[n];out.append(str(seq[pow(a,b,len(seq))]))
print('\n'.join(out))
