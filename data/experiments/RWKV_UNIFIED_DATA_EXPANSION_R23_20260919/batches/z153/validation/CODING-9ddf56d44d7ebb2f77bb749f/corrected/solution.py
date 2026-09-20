import sys,math
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
v=list(map(int,sys.stdin.buffer.read().split()));t,n,d=v[:3];counts=v[3:3+t];total=sum(counts);numerator=denominator=1
for j in range(n):
 color=v[3+t+2*j+1]-1;numerator*=counts[color];denominator*=total;counts[color]+=d;total+=d
g=math.gcd(numerator,denominator);print(str(numerator//g)+'/'+str(denominator//g))
