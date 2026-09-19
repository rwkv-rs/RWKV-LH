import sys
v=sys.stdin.read().split();out=[];bits=[1<<i for i in range(26)]
for case,s in enumerate(v[1:1+int(v[0])],1):
 first={0:-1};mask=0;best=0
 for i,c in enumerate(s):
  mask^=1<<(ord(c)-97);best=max(best,i-first.get(mask,i))
  for bit in bits:best=max(best,i-first.get(mask^bit,i))
  if mask not in first:first[mask]=i
 out.append(f'Case {case}: {best}')
print('\n'.join(out))
