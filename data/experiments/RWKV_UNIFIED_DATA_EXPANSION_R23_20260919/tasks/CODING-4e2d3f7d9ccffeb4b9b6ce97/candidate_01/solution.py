import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];print('Bob' if a.count(min(a))>n//2 else 'Alice')
