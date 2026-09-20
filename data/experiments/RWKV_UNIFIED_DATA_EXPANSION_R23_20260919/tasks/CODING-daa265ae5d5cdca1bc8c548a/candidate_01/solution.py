import sys
v=sys.stdin.buffer.read().split();rows,cols,k=map(int,v[:3]);grid=b''.join(v[3:]);n=rows*cols;start=grid.index(83);target=grid.index(84);adj=[[] for _ in range(n)]
for cell in range(n):
 y,x=divmod(cell,cols)
 for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
  yy=y+dy;xx=x+dx
  if 0<=yy<rows and 0<=xx<cols:adj[cell].append(yy*cols+xx)
prefixes=[(-1,0)];frontier=[(start,0,0)];seen=[set() for _ in range(n)];seen[start].add(0)
while frontier:
 following=[];i=0
 while i<len(frontier):
  prefix=frontier[i][2];buckets={}
  while i<len(frontier) and frontier[i][2]==prefix:
   cell,mask,_=frontier[i];i+=1
   for nxt in adj[cell]:
    if nxt==target:
     chars=[];p=prefix
     while p:parent,c=prefixes[p];chars.append(c);p=parent
     print(bytes(reversed(chars)).decode());raise SystemExit
    if nxt==start:continue
    c=grid[nxt];newmask=mask|1<<(c-97)
    if newmask.bit_count()<=k:buckets.setdefault(c,[]).append((nxt,newmask))
  for c in sorted(buckets):
   accepted=[]
   for cell,mask in buckets[c]:
    sub=mask;dominated=False
    while sub:
     if sub in seen[cell]:dominated=True;break
     sub=(sub-1)&mask
    if not dominated:seen[cell].add(mask);accepted.append((cell,mask))
   if accepted:
    newprefix=len(prefixes);prefixes.append((prefix,c));following.extend((cell,mask,newprefix) for cell,mask in accepted)
 frontier=following
print(-1)
