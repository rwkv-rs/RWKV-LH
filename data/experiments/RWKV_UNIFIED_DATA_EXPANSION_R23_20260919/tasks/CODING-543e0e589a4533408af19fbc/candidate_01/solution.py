import sys,collections,functools
v=sys.stdin.buffer.read().split();L,N=map(int,v[:2]);words=[w.decode() for w in v[2:]];words=sorted(set(words));words=[w for w in words if not any(w!=t and w in t for t in words)];N=len(words);edges=[{}];fail=[0];hit=[0]
for i,word in enumerate(words):
 u=0
 for c in word:
  if c not in edges[u]:edges[u][c]=len(edges);edges.append({});fail.append(0);hit.append(0)
  u=edges[u][c]
 hit[u]|=1<<i
queue=collections.deque(edges[0].values())
while queue:
 u=queue.popleft();hit[u]|=hit[fail[u]]
 for c,w in edges[u].items():
  f=fail[u]
  while f and c not in edges[f]:f=fail[f]
  fail[w]=edges[f].get(c,0);queue.append(w)
trans=[];grouped=[]
for u in range(len(edges)):
 row=[]
 for c in 'abcdefghijklmnopqrstuvwxyz':
  f=u
  while f and c not in edges[f]:f=fail[f]
  row.append(edges[f].get(c,0))
 trans.append(row);grouped.append(collections.Counter(row))
full=(1<<N)-1
@functools.lru_cache(None)
def count(rem,u,mask):
 if mask==full:return 26**rem
 if rem==0:return 0
 return sum(multiplicity*count(rem-1,w,mask|hit[w]) for w,multiplicity in grouped[u].items())
answer=count(L,0,0);out=[str(answer)]
if answer<=42:
 def emit(rem,u,mask,prefix):
  if not rem:out.append(prefix);return
  for i,w in enumerate(trans[u]):
   new=mask|hit[w]
   if count(rem-1,w,new):emit(rem-1,w,new,prefix+chr(97+i))
 if answer:emit(L,0,0,'')
print('\n'.join(out))
