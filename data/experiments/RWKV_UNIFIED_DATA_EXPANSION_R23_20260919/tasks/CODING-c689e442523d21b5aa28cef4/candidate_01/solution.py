import sys,math
values=list(map(int,sys.stdin.buffer.read().split()));out=[]
for a,b,c,d in zip(values[::4],values[1::4],values[2::4],values[3::4]):
 if a*d==b*c:
  g=math.gcd(abs(a),abs(b));x,y=a//g,b//g;h=c//x if x else d//y;out.append(str(math.gcd(g,abs(h))*(abs(x)+abs(y))));continue
 u=(a,b);v=(c,d)
 while True:
  nu=u[0]*u[0]+u[1]*u[1];nv=v[0]*v[0]+v[1]*v[1]
  if nv<nu:u,v=v,u;nu,nv=nv,nu
  dot=u[0]*v[0]+u[1]*v[1]
  if 2*abs(dot)<=nu:break
  k=(2*dot+nu)//(2*nu);v=(v[0]-k*u[0],v[1]-k*u[1])
 answer=min(abs(i*u[0]+j*v[0])+abs(i*u[1]+j*v[1]) for i in range(-2,3) for j in range(-2,3) if i or j);out.append(str(answer))
print('\n'.join(out))
