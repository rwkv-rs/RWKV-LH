import sys,math,functools
v=list(map(int,sys.stdin.buffer.read().split()));a=v[1:];flipped=False
while True:
 even=sum(x%2==0 for x in a)
 if even%2:win=True;break
 odds=[i for i,x in enumerate(a) if x%2]
 if len(odds)!=1 or a[odds[0]]==1:win=False;break
 a[odds[0]]-=1;g=functools.reduce(math.gcd,a);a=[x//g for x in a];flipped=not flipped
print('First' if win!=flipped else 'Second')
