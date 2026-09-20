import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n=next(it);m=next(it);r=next(it);player=next(it)-1;hands=[]
 for j in range(2):
  suits=[next(it) for i in range(n)];points=[next(it) for i in range(n)];hands.append(sorted(zip(points,suits)))
 suit=None;value=0
 while True:
  hand=hands[player];choice=0 if suit is None else next((i for i,(p,s) in enumerate(hand) if s==suit and p>value),-1)
  if choice<0:player^=1;suit=None;continue
  value,suit=hand.pop(choice)
  if not hand:out.append('FS wins!' if player==0 else 'FR wins!');break
  player^=1
print('\n'.join(out))
