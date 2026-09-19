import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);intervals=[(next(v)+1,next(v)+1,next(v)) for i in range(n)];limit=max(b for a,b,c in intervals);bit=[0]*(limit+1);parent=list(range(limit+1))
 def prefix(x):
  result=0
  while x:result+=bit[x];x-=x&-x
  return result
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 answer=0
 for a,b,c in sorted(intervals,key=lambda x:x[1]):
  need=c-prefix(b)+prefix(a-1)
  while need>0:
   x=find(b);p=x
   while p<=limit:bit[p]+=1;p+=p&-p
   parent[x]=find(x-1);need-=1;answer+=1
 out.append(str(answer))
print('\n'.join(out))
