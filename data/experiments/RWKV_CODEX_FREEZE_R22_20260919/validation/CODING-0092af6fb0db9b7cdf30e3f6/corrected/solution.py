import sys
a=sys.stdin.buffer.read().split();n=int(a[0]);sys.stdout.buffer.write(b' '.join(a[1:n+1][::-1])+b'\n')
