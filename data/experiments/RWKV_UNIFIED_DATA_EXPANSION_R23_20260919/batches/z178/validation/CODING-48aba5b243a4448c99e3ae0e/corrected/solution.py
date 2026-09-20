import sys,bisect
v=iter(sys.stdin.buffer.read().split());output=[];directions={b'U':(-1,0),b'D':(1,0),b'L':(0,-1),b'R':(0,1)}
for token in v:
 initial=int(token);maximum=int(next(v))
 if initial==maximum==0:break
 rows=int(next(v));cols=int(next(v));grid=[next(v) for _ in range(rows)];damage={}
 for _ in range(int(next(v))):char=next(v)[0];damage[char]=int(next(v))
 prefix=[0];r=c=0
 for _ in range(int(next(v))):
  dr,dc=directions[next(v)];steps=int(next(v))
  for j in range(steps):r+=dr;c+=dc;prefix.append(prefix[-1]+damage[grid[r][c]])
 potions=[int(next(v)) for _ in range(int(next(v)))];size=1<<len(potions);best=[-1]*size;best[0]=initial;success=False
 for mask,energy in enumerate(best):
  if energy<0:continue
  if energy>prefix[-1]:success=True;break
  position=bisect.bisect_left(prefix,energy)-1;before=prefix[position];health=energy-before
  for i,amount in enumerate(potions):
   if not mask>>i&1:
    new=mask|(1<<i);value=before+min(maximum,health+amount)
    if value>best[new]:best[new]=value
 output.append('YES' if success else 'NO')
print('\n'.join(output))
