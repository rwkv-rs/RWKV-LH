import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];need=[0]*n;required=0
for i in range(n-1,-1,-1):required=max(a[i]+1,required-1);need[i]=required
marks=0;answer=0
for i in range(n):marks=max(marks,need[i]);answer+=marks-a[i]-1
print(answer)
