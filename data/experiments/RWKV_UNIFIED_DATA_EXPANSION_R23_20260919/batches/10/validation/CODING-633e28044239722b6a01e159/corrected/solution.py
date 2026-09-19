import sys
v=sys.stdin.read().split();at=0;out=[]
while at<len(v):
 x=float(v[at]);y=float(v[at+1]);n=int(v[at+2]);at+=3;points=[(float(v[at+2*i]),float(v[at+2*i+1])) for i in range(n+1)];at+=2*(n+1);best=float('inf');answer=points[0]
 for (a,b),(c,d) in zip(points,points[1:]):
  u=c-a;w=d-b;length=u*u+w*w;t=min(1,max(0,((x-a)*u+(y-b)*w)/length)) if length else 0;p=a+t*u;q=b+t*w;distance=(p-x)**2+(q-y)**2
  if distance<best:best=distance;answer=p,q
 out.extend(format(z,'.4f') for z in answer)
print('\n'.join(out))
