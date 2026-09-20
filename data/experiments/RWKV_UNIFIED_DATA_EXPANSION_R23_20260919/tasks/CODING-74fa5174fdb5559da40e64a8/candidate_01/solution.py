import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];points=list(zip(v[1::2],v[2::2]));lx=min(x for x,y in points);ly=min(y for x,y in points);w=max(x for x,y in points)-lx+1;h=max(y for x,y in points)-ly+1;grid=[bytearray(h) for _ in range(w)]
for x,y in points:grid[x-lx][y-ly]=1
bad=[0]*(max(w,h)+1)
for k in range(3,len(bad)):bad[k]=math.comb(k,3)*(n-k)+math.comb(k,4)
answer=math.comb(n,4)
for col in grid:answer-=bad[sum(col)]
for y in range(h):answer-=bad[sum(col[y] for col in grid)]
for dx in range(1,(w-1)//2+1):
 for dy in range(1,(h-1)//2+1):
  if math.gcd(dx,dy)!=1:continue
  for direction in (1,-1):
   for x in range(w-2*dx):
    ymax=h-2*dy if x<dx else min(dy,h-2*dy)
    for y0 in range(ymax):
     y=y0 if direction==1 else h-1-y0;step=direction*dy;xx=x;count=0
     while xx<w and 0<=y<h:count+=grid[xx][y];xx+=dx;y+=step
     answer-=bad[count]
print(answer%1000000007)
