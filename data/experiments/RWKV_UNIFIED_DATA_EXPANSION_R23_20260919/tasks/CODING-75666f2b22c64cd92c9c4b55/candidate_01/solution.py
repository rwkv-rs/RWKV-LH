import sys
v=sys.stdin.read().split();n,a,b=map(int,v[:3]);s=v[3];answer=0
for run in s.split('*'):
 length=len(run)
 if a<b:a,b=b,a
 x=min(a,(length+1)//2);y=min(b,length//2);a-=x;b-=y;answer+=x+y
print(answer)
