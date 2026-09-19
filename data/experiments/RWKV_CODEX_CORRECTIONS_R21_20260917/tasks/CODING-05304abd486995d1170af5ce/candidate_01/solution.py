import sys
values=list(map(int,sys.stdin.buffer.read().split()));cache={};out=[]
for n,k in zip(values[::2],values[1::2]):
 if n==0:break
 if n not in cache:
  a=[0]*(2*n+1);seq=[]
  def db(t,p):
   if t>n:
    if n%p==0:seq.extend(a[1:p+1])
   else:
    a[t]=a[t-p];db(t+1,p)
    for j in range(a[t-p]+1,2):a[t]=j;db(t+1,t)
  db(1,1);cache[n]=seq
 seq=cache[n];v=0
 for j in range(n):v=(v<<1)|seq[(k+j)%len(seq)]
 out.append(str(v))
print('\n'.join(out))
