import sys
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));q=next(it);mana=next(it);N=1000002;bit=array('i',[0])*N;values={0:0};total=0
def change(y,d):
 global total
 total+=d;y+=1
 while y<N:bit[y]+=d;y+=y&-y
def prefix(y):
 y+=1;s=0
 while y>0:s+=bit[y];y-=y&-y
 return s
def kth(k):
 i=0;step=1<<19
 while step:
  j=i+step
  if j<N and bit[j]<k:k-=bit[j];i=j
  step>>=1
 return i
def remove(y):change(y,-1);del values[y]
def cross(a,b,c):return (b-a)*(values[c]-values[b])-(values[b]-values[a])*(c-b)
change(0,1);last_success=0;out=[]
for index in range(1,q+1):
 kind=next(it);aa=next(it);bb=next(it);x=(aa+last_success)%1000000+1;y=(bb+last_success)%1000000+1
 if kind==1:
  if y in values:
   if values[y]>=x:continue
   remove(y)
  rank=prefix(y);left=kth(rank)
  if values[left]>=x:continue
  right=kth(rank+1) if rank<total else None;values[y]=x
  if right is not None and cross(left,y,right)>=0:del values[y];continue
  while right is not None and values[right]<=x:
   remove(right);right=kth(rank+1) if rank<total else None
  while rank>=2:
   before=kth(rank-1)
   if cross(before,left,y)<0:break
   remove(left);rank-=1;left=before
  while rank+1<total:
   after=kth(rank+2)
   if cross(y,right,after)<0:break
   remove(right);right=after
  change(y,1)
 else:
  time=x;health=y;cap=mana//time
  rank=total if cap>=1000000 else prefix(cap);left=kth(rank)
  if rank==total:win=values[left]*time>=health
  else:
   right=kth(rank+1);win=(values[left]*time-health)*(right-left)+(values[right]-values[left])*(mana-left*time)>=0
  out.append('YES' if win else 'NO')
  if win:last_success=index
print('\n'.join(out))
