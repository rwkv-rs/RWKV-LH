import sys,math
y,lower=map(int,sys.stdin.read().split());answer=10
for a in range(1,10):
 for b in range(10):
  if a*10+b>=lower and (y-b)%a==0:answer=max(answer,(y-b)//a)
  for c in range(10):
   if a*100+b*10+c<lower:continue
   disc=b*b+4*a*(y-c);root=math.isqrt(disc)
   if root*root==disc and (root-b)%(2*a)==0:
    base=(root-b)//(2*a)
    if base>=10:answer=max(answer,base)
limit=int(y**(1/3))
while (limit+1)**3<=y:limit+=1
while limit**3>y:limit-=1
for base in range(limit,answer,-1):
 value=y;shown=0;place=1;valid=True
 while value:
  value,digit=divmod(value,base)
  if digit>9:valid=False;break
  shown+=digit*place;place*=10
 if valid and shown>=lower:answer=base;break
print(answer)
