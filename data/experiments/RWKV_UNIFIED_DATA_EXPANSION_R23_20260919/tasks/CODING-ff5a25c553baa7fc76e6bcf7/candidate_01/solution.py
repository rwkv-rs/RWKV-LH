import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
while True:
 a=next(v);d=next(v)
 if a==d==0:break
 attack=[next(v) for _ in range(a)];defend=sorted(next(v) for _ in range(d));out.append('Y' if min(attack)<defend[1] else 'N')
print('\n'.join(out))
