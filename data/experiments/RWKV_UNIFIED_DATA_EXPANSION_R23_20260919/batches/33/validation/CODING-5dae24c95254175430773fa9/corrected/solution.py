import sys
n,m=map(int,sys.stdin.read().split())
if m==0:print(int(n==0))
elif n<m:print(0)
else:print(int(((n-m)&((m-1)//2))==0))
