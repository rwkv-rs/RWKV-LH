import sys
k,a,b=map(int,sys.stdin.read().split());x,y=a//k,b//k
print(x+y if a%k<=y*(k-1) and b%k<=x*(k-1) and x+y>0 else -1)
