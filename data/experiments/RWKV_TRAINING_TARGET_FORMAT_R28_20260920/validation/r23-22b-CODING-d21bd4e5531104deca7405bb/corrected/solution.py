import sys,itertools
v=iter(sys.stdin.read().split());out=[]
for _ in range(int(next(v))):
 k=int(next(v));a=[next(v) for i in range(6)];b=[next(v) for i in range(6)];columns=[sorted({row[j] for row in a}&{row[j] for row in b}) for j in range(5)];answer='NO'
 for i,chars in enumerate(itertools.product(*columns),1):
  if i==k:answer=''.join(chars);break
 out.append(answer)
print('\n'.join(out))
