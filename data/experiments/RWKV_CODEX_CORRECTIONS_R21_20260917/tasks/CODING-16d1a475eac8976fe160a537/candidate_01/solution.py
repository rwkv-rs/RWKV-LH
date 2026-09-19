import sys
lines=sys.stdin.read().split();out=[]
for s in lines[1:]:
 chars={c:i for i,c in enumerate(sorted(set(s)))};k=len(chars);singles=0;pairs=[0]*k;triples=[0]*k
 for ch in s:
  c=chars[ch];mask=0
  for first in range(k):mask|=pairs[first]<<(first*k)
  triples[c]|=mask
  for first in range(k):
   if singles>>first&1:pairs[first]|=1<<c
  singles|=1<<c
 out.append(str(sum(x.bit_count() for x in triples)))
print('\n'.join(out))
