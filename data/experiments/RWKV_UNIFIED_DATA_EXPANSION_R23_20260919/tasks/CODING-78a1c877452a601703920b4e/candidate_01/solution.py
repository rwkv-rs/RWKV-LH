import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];points=[];zeros=0
for i in range(n):
 a,b,c=v[1+3*i:4+3*i]
 if c==0:zeros+=1
 else:points.append((a*c,b*c,a*a+b*b,1))
if zeros:points.append((0,0,1,zeros))
answer=zeros*(zeros-1)//2*(n-zeros)
for i,(x,y,d,weight) in enumerate(points):
 directions={}
 for xx,yy,dd,w in points[i+1:]:
  dx=xx*d-x*dd;dy=yy*d-y*dd;g=math.gcd(dx,dy);dx//=g;dy//=g
  if dx<0 or (dx==0 and dy<0):dx=-dx;dy=-dy
  key=(dx,dy);previous=directions.get(key,0);answer+=weight*w*previous;directions[key]=previous+w
print(answer)
