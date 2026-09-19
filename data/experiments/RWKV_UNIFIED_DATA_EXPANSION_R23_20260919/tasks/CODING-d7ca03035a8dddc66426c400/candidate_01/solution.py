import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 x=next(v);y=next(v);n=next(v);out.append(str(pow(x,y,n)))
print('\n'.join(out))
