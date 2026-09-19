import sys
v=list(map(int,sys.stdin.buffer.read().split()));k=v[0];a=v[1:1+k];b=v[1+k:1+2*k];answer=0;modulus=1
for remainder,divisor in zip(a,b):
 if divisor==1:continue
 step=(remainder-answer)*pow(modulus,-1,divisor)%divisor;answer+=modulus*step;modulus*=divisor;answer%=modulus
print(answer)
