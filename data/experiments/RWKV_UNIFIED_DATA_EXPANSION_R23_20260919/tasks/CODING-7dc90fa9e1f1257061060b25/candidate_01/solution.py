import sys
v=iter(sys.stdin.buffer.read().split());n=int(next(v));groups=[]
for _ in range(n):groups.append([next(v) for j in range(int(next(v)))])
total=sum(map(len,groups));size=(total+7)//8;contains=[bytearray(size) for _ in range(n)];ranges=[];offset=0
for group in groups:
 ranges.append(((1<<len(group))-1)<<offset)
 for word in group:
  byte,bit=divmod(offset,8);mask=1<<bit
  for char in word:contains[char-97][byte]|=mask
  offset+=1
contains=[int.from_bytes(row,'little') for row in contains];all_options=(1<<total)-1;del groups
answer=[[-1]*n for _ in range(n)]
for goal in range(n):
 reached=1<<goal;answer[goal][goal]=0;steps=0
 while True:
  blocked=0
  for u in range(n):
   if not reached>>u&1:blocked|=contains[u]
  allowed=all_options^blocked;new=0
  for u in range(n):
   if not reached>>u&1 and allowed&ranges[u]:new|=1<<u
  if not new:break
  steps+=1
  for u in range(n):
   if new>>u&1:answer[u][goal]=steps
  reached|=new
print('\n'.join(' '.join(map(str,row)) for row in answer))
