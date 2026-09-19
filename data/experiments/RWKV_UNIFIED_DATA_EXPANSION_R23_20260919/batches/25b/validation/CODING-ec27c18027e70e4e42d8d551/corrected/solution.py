import sys
out=[]
for n in map(int,sys.stdin.read().split()):
 if n==0:break
 x=abs(n);f=['-1'] if n<0 else [];p=2
 while p*p<=x:
  while x%p==0:f.append(str(p));x//=p
  p=3 if p==2 else p+2
 if x>1:f.append(str(x))
 out.append(str(n)+' = '+' x '.join(f))
print('\n'.join(out))
