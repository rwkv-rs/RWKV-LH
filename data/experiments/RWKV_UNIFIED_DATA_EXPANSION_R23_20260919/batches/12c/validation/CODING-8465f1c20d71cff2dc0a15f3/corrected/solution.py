import sys
v=list(map(int,sys.stdin.buffer.read().split()));print('\n'.join(str(s+(s-1)//9) for s in v[1:1+v[0]]))
