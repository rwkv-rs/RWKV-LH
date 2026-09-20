import sys,math
values=list(map(int,sys.stdin.buffer.read().split()))[1:];out=[]
for n in values:
 even=odd=0;p=2
 while p*p<=n:
  if n%p==0:
   exponent=0
   while n%p==0:n//=p;exponent+=1
   if exponent%2:odd+=1
   else:even+=1
  p=3 if p==2 else p+2
 if n>1:odd+=1
 out.append('Psycho Number' if even>odd else 'Ordinary Number')
print('\n'.join(out))
