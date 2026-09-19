import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 ident=next(v);base=next(v);x=next(v);y=next(v);answer=0;place=1
 while x or y:answer+=((x%base+y%base)%base)*place;x//=base;y//=base;place*=base
 out.append(str(ident)+' '+str(answer))
print('\n'.join(out))
