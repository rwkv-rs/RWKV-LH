import sys,bisect
v=sys.stdin.buffer.read().split();n,q=map(int,v[:2]);p=2;deficit=0;previous=0;intervals=[]
for _ in range(n):
 sign=v[p];time=int(v[p+1]);count=int(v[p+2]);p+=3
 if deficit>0:intervals.append((deficit,time-previous))
 deficit+=count if sign==b'-' else -count;previous=time
intervals.sort();levels=[x for x,t in intervals];weights=[0]*(len(levels)+1);areas=[0]*(len(levels)+1)
for i in range(len(levels)-1,-1,-1):
 x,t=intervals[i];weights[i]=weights[i+1]+t;areas[i]=areas[i+1]+x*t
out=[]
for b in map(int,v[p:p+q]):
 if b<deficit:out.append('INFINITY')
 else:
  i=bisect.bisect_right(levels,b);out.append(str(areas[i]-b*weights[i]))
print('\n'.join(out))
