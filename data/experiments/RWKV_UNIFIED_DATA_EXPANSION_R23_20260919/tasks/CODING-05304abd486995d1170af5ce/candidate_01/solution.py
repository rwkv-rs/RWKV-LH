import sys
v=iter(map(int,sys.stdin.read().split()));cache={};out=[]
for n,k in zip(v,v):
 if n==0:break
 if n not in cache:
  a=[0]*(n+1);sequence=[]
  def generate(t,p):
   if t>n:
    if n%p==0:sequence.extend(a[1:p+1])
   else:
    a[t]=a[t-p];generate(t+1,p)
    for digit in range(a[t-p]+1,2):a[t]=digit;generate(t+1,t)
  generate(1,1);cache[n]=sequence
 s=cache[n];value=0
 for i in range(n):value=value*2+s[(k+i)%len(s)]
 out.append(str(value))
print('\n'.join(out))
