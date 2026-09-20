import sys
v=list(map(int,sys.stdin.buffer.read().split()));P=4294967143;inverse=pow(12,-1,P);powers=[(2,1)]
for _ in range(64):a,b=powers[-1];powers.append(((a*a+3*b*b)%P,2*a*b%P))
out=[]
for n in v[1:]:
 if n%2:out.append('0');continue
 t=n//2;a,b=1,0;bits=t;i=0
 while bits:
  if bits&1:c,d=powers[i];a,b=(a*c+3*b*d)%P,(a*d+b*c)%P
  bits//=2;i+=1
 answer=(44*a+6*b+23*pow(3,t,P)+22*pow(2,t,P)+21)*inverse%P;out.append(str(answer))
print('\n'.join(out))
