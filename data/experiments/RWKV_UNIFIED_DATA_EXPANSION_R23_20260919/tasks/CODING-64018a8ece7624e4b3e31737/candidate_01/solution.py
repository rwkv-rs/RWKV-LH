import sys
out=[]
for n in map(int,sys.stdin.buffer.read().split()):
 if n==0:break
 out.append('Alice' if n%2==0 else 'Bob')
print('\n'.join(out))
