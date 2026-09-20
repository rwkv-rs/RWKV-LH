import sys,bisect
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));p=0;out=[]
while p<len(v):
 n,m=v[p:p+2];p+=2
 if n==m==0:break
 cats=[]
 for _ in range(n):x,y,c=v[p:p+3];p+=3;cats.append((2*x,c))
 bowls=sorted(v[p:p+m]);p+=m;cats.sort();xs=[x for x,c in cats];prefix=[0]
 for x,c in cats:prefix.append(prefix[-1]+c)
 total=prefix[-1];cut=[array('i',[0])*m for _ in range(m)]
 for i in range(m):
  for j in range(i+1,m):cut[i][j]=prefix[bisect.bisect_right(xs,bowls[i]+bowls[j])]
 def feasible(limit):
  incoming=[0]*m
  for i in range(m):
   value=incoming[i]
   if total-value<=limit:return True
   row=cut[i]
   for j in range(i+1,m):
    w=row[j]
    if w-value<=limit and w>incoming[j]:incoming[j]=w
  return False
 low,high=0,total
 while low<high:
  mid=(low+high)//2
  if feasible(mid):high=mid
  else:low=mid+1
 out.append(str(low))
print('\n'.join(out))
