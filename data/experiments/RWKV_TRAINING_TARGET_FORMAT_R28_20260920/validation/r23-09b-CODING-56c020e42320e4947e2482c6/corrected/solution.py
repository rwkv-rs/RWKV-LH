import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n=next(it);answer=0
 for _ in range(n):answer+=next(it)-next(it)
 out.append(str(answer))
print('\n'.join(out))
