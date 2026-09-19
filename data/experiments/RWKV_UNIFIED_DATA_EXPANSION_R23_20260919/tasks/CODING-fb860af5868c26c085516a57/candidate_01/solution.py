import sys,math
v=iter(map(int,sys.stdin.read().split()));out=[]
while True:
 try:n=next(v)
 except StopIteration:break
 if n==0:break
 c1=next(v);n1=next(v);c2=next(v);n2=next(v);g=math.gcd(n1,n2)
 if n%g:out.append('failed');continue
 a=n1//g;b=n2//g;total=n//g;x=(total*pow(a,-1,b))%b if b>1 else 0;y=(total-a*x)//b
 if y<0:out.append('failed');continue
 steps=y//a
 if c1*b<c2*a:x+=steps*b;y-=steps*a
 out.append(f'{x} {y}')
print('\n'.join(out))
