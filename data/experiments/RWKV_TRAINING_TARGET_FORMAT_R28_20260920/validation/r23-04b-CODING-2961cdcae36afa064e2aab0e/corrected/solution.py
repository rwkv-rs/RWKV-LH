import sys,math
from collections import Counter
from functools import cmp_to_key
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2]
def direction(x,y):
 g=math.gcd(abs(x),abs(y));return x//g,y//g
stars=Counter(direction(v[2+2*i],v[3+2*i]) for i in range(n));queries=[direction(v[2+2*n+2*i],v[3+2*n+2*i]) for i in range(m)];allpoints=set(stars)|set(queries)|{(1,0)}
def compare(a,b):
 ax,ay=a;bx,by=b;ha=0 if ay>0 or ay==0 and ax>0 else 1;hb=0 if by>0 or by==0 and bx>0 else 1
 if ha!=hb:return ha-hb
 cross=ax*by-ay*bx;return -1 if cross>0 else 1 if cross<0 else 0
ordered=sorted(allpoints,key=cmp_to_key(compare));index={p:i for i,p in enumerate(ordered)};prefix=[0]
for p in ordered:prefix.append(prefix[-1]+stars[p])
start=(1,0);out=[]
for end in queries:
 a=index[start];b=index[end]
 forward=prefix[b+1]-prefix[a] if a<=b else n-prefix[a]+prefix[b+1]
 backward=n-forward+stars[start]+stars[end];out.append(str(max(forward,backward)));start=end
print('\n'.join(out))
