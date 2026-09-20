import sys
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(v)):
 n,x,y=next(v),next(v),next(v);out.append(str(min(n,max(1,x+y-n+1)))+' '+str(min(n,x+y-1)))
print('\n'.join(out))
