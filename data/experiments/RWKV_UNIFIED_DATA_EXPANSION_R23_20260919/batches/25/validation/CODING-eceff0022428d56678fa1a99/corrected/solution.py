import sys
v=sys.stdin.read().split();n,k=map(int,v[:2]);cards=[s.encode() for s in v[2:]];index={s:i for i,s in enumerate(cards)};answer=0
for i,a in enumerate(cards):
 for j in range(i+1,n):
  b=cards[j];third=bytes(x if x==y else 236-x-y for x,y in zip(a,b))
  if index.get(third,-1)>j:answer+=1
print(answer)
