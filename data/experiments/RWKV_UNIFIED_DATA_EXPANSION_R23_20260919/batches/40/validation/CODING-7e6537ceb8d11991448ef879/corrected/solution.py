import sys
n,m=sorted(map(int,sys.stdin.buffer.read().split()))
if n==1:answer=m//6*6+max(0,m%6-3)*2
elif n==2:
 if m==2:answer=0
 elif m in (3,7):answer=2*m-2
 else:answer=2*m
else:answer=n*m//2*2
print(answer)
