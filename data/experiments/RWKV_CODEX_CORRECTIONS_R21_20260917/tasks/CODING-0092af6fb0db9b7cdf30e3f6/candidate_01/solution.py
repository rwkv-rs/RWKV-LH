import sys
a=list(map(int,sys.stdin.buffer.read().split()));print(*a[1:1+a[0]][::-1])
