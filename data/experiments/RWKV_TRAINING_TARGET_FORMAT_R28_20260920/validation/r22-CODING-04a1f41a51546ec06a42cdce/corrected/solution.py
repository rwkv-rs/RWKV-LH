import sys
a=list(map(int,sys.stdin.buffer.read().split()));print('\n'.join(f'{a[i]-1} {a[i+1]}' for i in range(1,len(a),2)))
