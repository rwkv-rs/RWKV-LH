import sys
from itertools import groupby
v=sys.stdin.read().split();out=[]
for s in v[1:1+int(v[0])]:
 runs=[c for c,g in groupby(s)];out.append('YES' if runs==runs[::-1] else 'NO')
print('\n'.join(out))
