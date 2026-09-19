import sys
a=list(map(int,sys.stdin.buffer.read().split()));print('\n'.join('Roy wins!' if n%6==0 else 'October wins!' for n in a[1:1+a[0]]))
