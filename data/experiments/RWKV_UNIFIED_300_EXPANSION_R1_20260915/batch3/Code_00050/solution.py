import sys
a=list(map(int,sys.stdin.buffer.read().split()));n=a[0];p=a[1:];pos=[0]*(n+1)
for i,v in enumerate(p,1):pos[v]=i
left=list(range(-1,n+1));right=list(range(1,n+3));ans=0
# Remove smaller values; surviving adjacent indices are the nearest greater values.
for value in range(1,n+1):
    i=pos[value];l=left[i];r=right[i]
    ll=left[l] if l else 0;rr=right[r] if r<=n else n+1
    ans+=value*((l-ll)*(r-i)+(rr-r)*(i-l))
    right[l]=r;left[r]=l
print(ans)
