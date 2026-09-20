import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));factorial=[math.factorial(i) for i in range(51)];ways=[1]+[0]*50
for n in range(1,51):ways[n]=sum((1 if size==1 else factorial[size-2])*ways[n-size] for size in range(1,n+1))
out=[]
for case in range(v[0]):
 n,k=v[1+2*case:3+2*case]
 if k>ways[n]:out.append('-1');continue
 answer=[];offset=0
 while n:
  for size in range(1,n+1):
   count=(1 if size==1 else factorial[size-2])*ways[n-size]
   if k>count:k-=count
   else:break
  if size==1:answer.append(offset+1);offset+=1;n-=1;continue
  tailways=ways[n-size];blockrank=(k-1)//tailways+1;k=(k-1)%tailways+1;parent=list(range(size))
  def root(x):
   while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
   return x
  parent[0]=size-1;block=[size];available=list(range(size-1))
  for position in range(1,size):
   for value in available:
    if position!=size-1 and root(position)==root(value):continue
    count=factorial[max(0,size-position-2)]
    if blockrank>count:blockrank-=count
    else:
     block.append(value+1);parent[root(position)]=root(value);available.remove(value);break
  answer.extend(offset+x for x in block);offset+=size;n-=size
 out.append(' '.join(map(str,answer)))
print('\n'.join(out))
