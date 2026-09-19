import sys
v=iter(sys.stdin.read().split());index={}
for i in range(1,int(next(v))+1):
 words={next(v) for _ in range(int(next(v)))}
 for word in words:index.setdefault(word,[]).append(str(i))
out=[' '.join(index.get(next(v),[])) for _ in range(int(next(v)))];sys.stdout.write('\n'.join(out)+'\n')
