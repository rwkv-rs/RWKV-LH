import sys
v=sys.stdin.read().split();n,k=map(int,v[:2]);trie=[{}]
for s in v[2:]:
 p=0
 for c in s:
  if c not in trie[p]:trie[p][c]=len(trie);trie.append({})
  p=trie[p][c]
win=[False]*len(trie);lose=[False]*len(trie)
for p in range(len(trie)-1,-1,-1):
 children=list(trie[p].values())
 if not children:lose[p]=True
 else:win[p]=any(not win[q] for q in children);lose[p]=any(not lose[q] for q in children)
print('First' if win[0] and (lose[0] or k%2) else 'Second')
