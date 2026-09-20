import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];points=list(zip(v[1::2],v[2::2]));perimeter=sum(abs(a-c)+abs(b-d) for (a,b),(c,d) in zip(points,points[1:]+points[:1]));xs=[x for x,y in points];ys=[y for x,y in points]
print(perimeter-2*(max(xs)-min(xs)+max(ys)-min(ys)))
