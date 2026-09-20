import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n,m,q=v[:3];stride=m+2;size=(n+2)*stride;right=array('i',range(1,size+1));down=array('i',range(stride,size+stride));value=array('i',[0])*size
for i in range(n):value[(i+1)*stride+1:(i+1)*stride+m+1]=array('i',v[3+i*m:3+(i+1)*m])
def at(r,c):
 u=0
 for _ in range(r):u=down[u]
 for _ in range(c):u=right[u]
 return u
def boundary(a,b,h,w):
 u=at(a-1,b-1);top=[];left=[];x=u
 for _ in range(w):x=right[x];top.append(x)
 x=u
 for _ in range(h):x=down[x];left.append(x)
 x=left[-1];bottom=[]
 for _ in range(w):x=right[x];bottom.append(x)
 x=top[-1];side=[]
 for _ in range(h):x=down[x];side.append(x)
 return top,bottom,left,side
p=3+n*m
for _ in range(q):
 a,b,c,d,h,w=v[p:p+6];p+=6;one=boundary(a,b,h,w);two=boundary(c,d,h,w)
 for edge in range(4):
  links=down if edge<2 else right
  for x,y in zip(one[edge],two[edge]):links[x],links[y]=links[y],links[x]
out=[];start=0
for i in range(n):
 start=down[start];u=start;line=[]
 for j in range(m):u=right[u];line.append(str(value[u]))
 out.append(' '.join(line))
print('\n'.join(out))
