import sys
lines=sys.stdin.buffer.read().split();s,t=lines[:2];q=int(lines[2]);data=list(map(int,lines[3:]))
def prepare(s):
 p=[0];last=[0]
 for i,c in enumerate(s,1):p.append(p[-1]+(c!=65));last.append(i if c!=65 else last[-1])
 return p,last
sp,sl=prepare(s);tp,tl=prepare(t);out=[]
for i in range(0,4*q,4):
 a,b,c,d=data[i:i+4];x=sp[b]-sp[a-1];y=tp[d]-tp[c-1];u=b-max(a-1,sl[b]);v=d-max(c-1,tl[d]);gap=u-v
 ok=x<=y and (y-x)%2==0 and gap>=0
 if x==y:ok=ok and gap%3==0
 elif x==0:ok=ok and gap>0
 out.append('1' if ok else '0')
print(''.join(out))
