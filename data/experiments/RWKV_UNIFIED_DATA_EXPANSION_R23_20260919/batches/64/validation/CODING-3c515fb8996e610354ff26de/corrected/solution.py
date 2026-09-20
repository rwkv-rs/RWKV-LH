import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];children=[[] for _ in range(n)];distance=[0]*n;P=[0]*n;Q=[0]*n;edge=[0]*n
for i in range(1,n):
 parent,length,p,q=v[1+4*(i-1):5+4*(i-1)];children[parent-1].append(i);edge[i]=length;P[i]=p;Q[i]=q
order=[0]
for u in order:
 for w in children[u]:distance[w]=distance[u]+edge[w];order.append(w)
answer=[0]*n;slopes=[0]*n;intercepts=[0]*n;length=1;stack=[(0,False,None)]
def bad(i,m,b):return (intercepts[i]-intercepts[i-1])*(slopes[i]-m)>=(b-intercepts[i])*(slopes[i-1]-slopes[i])
while stack:
 u,leaving,record=stack.pop()
 if leaving:
  if record is not None:
   at,oldm,oldb,oldlength=record;slopes[at]=oldm;intercepts[at]=oldb;length=oldlength
  continue
 if u:
  x=P[u];lo,hi=0,length-1
  while lo<hi:
   mid=(lo+hi)//2
   if slopes[mid]*x+intercepts[mid]>=slopes[mid+1]*x+intercepts[mid+1]:lo=mid+1
   else:hi=mid
  answer[u]=distance[u]*x+Q[u]+slopes[lo]*x+intercepts[lo];m,b=-distance[u],answer[u];oldlength=length
  if m==slopes[length-1] and b>=intercepts[length-1]:record=None
  else:
   searchlength=length-int(m==slopes[length-1]);lo,hi=1,searchlength
   while lo<hi:
    mid=(lo+hi)//2
    if bad(mid,m,b):hi=mid
    else:lo=mid+1
   at=lo if searchlength else 0;record=(at,slopes[at],intercepts[at],oldlength);slopes[at]=m;intercepts[at]=b;length=at+1
 stack.append((u,True,record))
 for w in reversed(children[u]):stack.append((w,False,None))
print('\n'.join(map(str,answer[1:])))
