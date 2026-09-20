import sys
v=list(map(int,sys.stdin.buffer.read().split()));print('\n'.join(str(max(0,n-2)) for n in v[1:1+v[0]]))
