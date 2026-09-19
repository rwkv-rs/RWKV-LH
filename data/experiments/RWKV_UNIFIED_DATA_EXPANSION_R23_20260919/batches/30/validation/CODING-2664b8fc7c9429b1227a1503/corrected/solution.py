import sys
v=list(map(int,sys.stdin.read().split()));white=v[:4];a=v[4:8];b=v[8:12]
def intersection(*rects):return [max(r[0] for r in rects),max(r[1] for r in rects),min(r[2] for r in rects),min(r[3] for r in rects)]
def area(r):return max(0,r[2]-r[0])*max(0,r[3]-r[1])
covered=area(intersection(white,a))+area(intersection(white,b))-area(intersection(white,a,b));print('YES' if covered<area(white) else 'NO')
