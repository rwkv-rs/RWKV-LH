import sys
from collections import Counter
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 count=Counter(next(v) for i in range(next(v)))
 out.extend(f'{x}: {count[x]}' for x in sorted(count))
print('\n'.join(out))
