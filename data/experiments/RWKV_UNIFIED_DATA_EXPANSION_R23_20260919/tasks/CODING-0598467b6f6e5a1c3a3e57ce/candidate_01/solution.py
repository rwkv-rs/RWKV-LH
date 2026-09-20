import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));n,q=next(it),next(it);heap=[];by_left={};by_right={};students={};bit={};out=[]
def add(l,r):
 if l<=r:by_left[l]=r;by_right[r]=l;heapq.heappush(heap,(-(r-l+1),-r,l))
def remove(l,r):del by_left[l];del by_right[r]
def update(p,delta):
 while p<=n:bit[p]=bit.get(p,0)+delta;p+=p&-p
def prefix(p):
 value=0
 while p:value+=bit.get(p,0);p-=p&-p
 return value
add(1,n)
for _ in range(q):
 student=next(it)
 if student==0:l,r=next(it),next(it);out.append(str(prefix(r)-prefix(l-1)));continue
 if student in students:
  p=students.pop(student);update(p,-1);l=r=p
  if p-1 in by_right:l=by_right[p-1];remove(l,p-1)
  if p+1 in by_left:r=by_left[p+1];remove(p+1,r)
  add(l,r)
 else:
  while True:
   neglen,negr,l=heapq.heappop(heap);r=-negr
   if by_left.get(l)==r:break
  remove(l,r);p=(l+r+1)//2;students[student]=p;update(p,1);add(l,p-1);add(p+1,r)
print('\n'.join(out))
