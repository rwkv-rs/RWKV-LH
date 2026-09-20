import sys
v=iter(map(int,sys.stdin.buffer.read().split()));tests=next(v);out=[]
for _ in range(tests):
 n=next(v);time=0;a=1;b=1;c=2;d=1;okay=True
 for j in range(n):
  t=next(v);x=next(v);y=next(v);X=next(v);Y=next(v);elapsed=t-time
  if x not in (1,2) or X not in (1,2) or y<b or Y<d or (x==X and y==Y) or y-b+(x!=a)>elapsed or Y-d+(X!=c)>elapsed:okay=False
  time,a,b,c,d=t,x,y,X,Y
 out.append('yes' if okay else 'no')
print('\n'.join(out))
