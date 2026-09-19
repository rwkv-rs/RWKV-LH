import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for k,x,y in zip(v,v,v):
 if k==x==y==0:break
 answer=0;stack=[(1024,1024,k)]
 while stack:
  cx,cy,size=stack.pop()
  if abs(x-cx)>2*size or abs(y-cy)>2*size:continue
  if abs(x-cx)<=size and abs(y-cy)<=size:answer+=1
  if size>1:
   for dx in (-size,size):
    for dy in (-size,size):stack.append((cx+dx,cy+dy,size//2))
 out.append(f'{answer:3d}')
print('\n'.join(out))
