import sys,itertools,collections,functools
vertices=list(itertools.product((-1,1),repeat=3));edges=[(a,b) for a in vertices for b in vertices if a<b and sum(x!=y for x,y in zip(a,b))==1];lookup={edge:i for i,edge in enumerate(edges)};types=collections.Counter()
for perm in itertools.permutations(range(3)):
 parity=(-1)**sum(perm[i]>perm[j] for i in range(3) for j in range(i+1,3))
 for signs in itertools.product((-1,1),repeat=3):
  if parity*signs[0]*signs[1]*signs[2]!=1:continue
  mapping=[]
  for a,b in edges:
   aa=tuple(signs[i]*a[perm[i]] for i in range(3));bb=tuple(signs[i]*b[perm[i]] for i in range(3));mapping.append(lookup[tuple(sorted((aa,bb)))])
  seen=set();cycles=[]
  for i in range(12):
   if i in seen:continue
   length=0
   while i not in seen:seen.add(i);length+=1;i=mapping[i]
   cycles.append(length)
  types[tuple(sorted(cycles,reverse=True))]+=1
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for test in range(v[0]):
 counts=tuple(collections.Counter(v[1+12*test:13+12*test]).values());total=0
 for cycles,multiple in types.items():
  @functools.lru_cache(None)
  def fixed(i,left):
   if i==len(cycles):return 1
   length=cycles[i];answer=0
   for j,num in enumerate(left):
    if num>=length:changed=list(left);changed[j]-=length;answer+=fixed(i+1,tuple(changed))
   return answer
  total+=multiple*fixed(0,counts)
 out.append(str(total//24))
print('\n'.join(out))
