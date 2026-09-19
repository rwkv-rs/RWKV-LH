import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];initial=v[2:2+n][::-1];coef=v[2+n:2+2*n];mod=4147
def multiply(a,b):
 c=[0]*(2*n-1)
 for i,x in enumerate(a):
  for j,y in enumerate(b):c[i+j]=(c[i+j]+x*y)%mod
 for degree in range(2*n-2,n-1,-1):
  value=c[degree]
  for j,x in enumerate(coef):c[degree-j-1]=(c[degree-j-1]+value*x)%mod
 return c[:n]
result=[1]+[0]*(n-1);power=([0,1]+[0]*(n-2)) if n>1 else [coef[0]];exponent=m-1
while exponent:
 if exponent&1:result=multiply(result,power)
 power=multiply(power,power);exponent//=2
print(sum(x*y for x,y in zip(result,initial))%mod)
