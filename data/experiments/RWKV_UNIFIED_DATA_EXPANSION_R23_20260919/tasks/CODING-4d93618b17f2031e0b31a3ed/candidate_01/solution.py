import sys
from collections import Counter
v=sys.stdin.buffer.read().split();out=[]
for word in v[1:]:
 permutation=[x-65 for x in word];seen=set();cycles=Counter()
 for i in range(26):
  if i in seen:continue
  size=0;u=i
  while u not in seen:seen.add(u);size+=1;u=permutation[u]
  cycles[size]+=1
 out.append('Yes' if all(size%2 or number%2==0 for size,number in cycles.items()) else 'No')
print('\n'.join(out))
