import sys
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for n in v[1:1+v[0]]:
 survivor=0
 for remaining in range(2,n+1):survivor=(survivor+n-remaining+1)%remaining
 out.append(str(survivor+1))
print('\n'.join(out))
