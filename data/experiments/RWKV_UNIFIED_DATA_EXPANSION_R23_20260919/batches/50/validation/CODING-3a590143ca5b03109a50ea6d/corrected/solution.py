import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[];cache={}
for _ in range(next(it)):
 n,Q=next(it),next(it);coins=[next(it) for i in range(n)];key=(n.bit_length(),Q)
 if key not in cache:
  limit=n.bit_length();g=[[0]*limit for _ in range(limit)]
  for a in range(limit):
   for b in range(limit):
    moves=set()
    for p in range(1,a+1):
     value=0
     for q in range(1,min(Q,a//p)+1):value^=g[a-p*q][b];moves.add(value)
    for p in range(1,b+1):
     value=0
     for q in range(1,min(Q,b//p)+1):value^=g[a][b-p*q];moves.add(value)
    value=0
    while value in moves:value+=1
    g[a][b]=value
  cache[key]=g
 g=cache[key];value=0
 for x,coin in enumerate(coins,1):
  if coin:continue
  a=b=0
  while x%2==0:a+=1;x//=2
  while x%3==0:b+=1;x//=3
  value^=g[a][b]
 out.append('win' if value else 'lose')
print('\n'.join(out))
