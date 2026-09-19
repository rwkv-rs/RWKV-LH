import sys
v=list(map(int,sys.stdin.buffer.read().split()));print('\n'.join('Case #'+str(i)+': '+str(2*n-1) for i,n in enumerate(v[1:1+v[0]],1)))
