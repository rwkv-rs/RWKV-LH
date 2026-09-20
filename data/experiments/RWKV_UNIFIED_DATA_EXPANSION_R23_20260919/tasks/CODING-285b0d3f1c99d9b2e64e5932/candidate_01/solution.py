import sys
v=list(map(int,sys.stdin.buffer.read().split()));left,top,right,bottom=v[:4];n=v[4];points=list(zip(v[5::2],v[6::2]));events={}
for i,(x,y) in enumerate(points):
 xx,yy=points[(i+1)%n]
 if y!=yy:continue
 lo=max(left,min(x,xx));hi=min(right,max(x,xx))
 if lo<hi:events[y]=events.get(y,0)^(((1<<(hi-lo))-1)<<(lo-left))
def corners(lower,upper):
 a=lower<<1;b=lower;c=upper<<1;d=upper;odd=a^b^c^d;pairs=(a&b)|(a&c)|(a&d)|(b&c)|(b&d)|(c&d);one=odd&~pairs;three=odd&pairs;diagonal=(a&d&~b&~c)|(b&c&~a&~d);return one.bit_count()-three.bit_count()+2*diagonal.bit_count()
current=0
for y,change in events.items():
 if y<=bottom:current^=change
score=corners(0,current)
for y in sorted(events):
 if bottom<y<top:
  following=current^events[y];score+=corners(current,following);current=following
score+=corners(current,0);print(score//4)
