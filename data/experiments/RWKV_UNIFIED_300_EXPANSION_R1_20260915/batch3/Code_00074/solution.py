import sys,math,bisect
a=iter(map(int,sys.stdin.buffer.read().split()));n=next(a);points=[(next(a),next(a)) for _ in range(n)];right=obtuse=0;pi=math.pi;eps=1e-10
for x,y in points:
    angles=sorted(math.atan2(v-y,u-x) for u,v in points if (u,v)!=(x,y));m=len(angles);angles+=[v+2*pi for v in angles]
    for i in range(m):
        angle=angles[i];r1=bisect.bisect_left(angles,angle+pi/2-eps,i+1,i+m);r2=bisect.bisect_right(angles,angle+pi/2+eps,r1,i+m);end=bisect.bisect_left(angles,angle+pi-eps,r2,i+m)
        right+=r2-r1;obtuse+=end-r2
print(n*(n-1)*(n-2)//6-right-obtuse,right,obtuse)
