import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));mod=1000000007;out=[]
for i in range(v[0]):
 a,b=sorted(v[1+2*i:3+2*i]);answer=0
 if b==25 and 0<=a<=23:answer=math.comb(24+a,a)%mod
 elif a>=24 and b==a+2:answer=math.comb(48,24)*pow(2,a-24,mod)%mod
 out.append(str(answer))
print('\n'.join(out))
