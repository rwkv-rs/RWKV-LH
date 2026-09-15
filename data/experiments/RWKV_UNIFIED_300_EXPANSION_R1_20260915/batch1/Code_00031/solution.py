import sys
a=list(map(int,sys.stdin.buffer.read().split()));n=a[0]-1;s=a[1:];ans=0
for d in range(1,n):
    total=0
    for k in range(1,(n-1)//d):
        if n%d==0 and 2*k*d>=n:break
        total+=s[k*d]+s[n-k*d]
        ans=max(ans,total)
print(ans)
