import sys
v=list(map(int,sys.stdin.read().split()));n=v[0];a=v[1:];i=n-1
while i>0 and a[i-1]<a[i]:i-=1
print(i)
