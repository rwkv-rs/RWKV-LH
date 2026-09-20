import sys,math
k=int(sys.stdin.buffer.read());total=0;a=1;limit=4*k*k
while True:
 remaining=limit-(3*a+1)**2
 if remaining<0:break
 b=(math.isqrt(remaining//3)-a-1)//2
 if b<0:break
 total+=b+1;a+=1
print(1+6*total)
