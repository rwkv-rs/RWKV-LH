import sys,math
def solve(a,p,b):
 a%=p;b%=p
 if b==1%p:return 0
 factor=1;offset=0
 while True:
  g=math.gcd(a,p)
  if g==1:break
  if b%g:return None
  b//=g;p//=g;factor=factor*(a//g)%p;offset+=1
  if factor==b:return offset
 if p==1:return offset
 target=b*pow(factor,-1,p)%p;size=math.isqrt(p)+1;baby={};value=1
 for j in range(size):baby.setdefault(value,j);value=value*a%p
 jump=pow(pow(a,size,p),-1,p);value=target
 for i in range(size+1):
  if value in baby:return offset+i*size+baby[value]
  value=value*jump%p
 return None
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i in range(0,len(v),3):
 a,p,b=v[i:i+3]
 if a==p==b==0:break
 answer=solve(a,p,b);out.append('No Solution' if answer is None else str(answer))
print('\n'.join(out))
