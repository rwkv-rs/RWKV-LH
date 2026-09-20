import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];b=[0]*n
for i in range(1,n-1):b[i]=min(a[i],max(a[i-1],a[i+1]))
size=(n+1)//2;plain=[0]*size;odd=[0]*size;x=y=0
for d in range(size-1,-1,-1):
 x=max(x,a[d],a[n-1-d]);y=max(y,b[d],b[n-1-d]);plain[d]=x;odd[d]=y
out=[]
for length in range(n,0,-1):
 value=plain[0] if length==1 else plain[length//2-1] if length%2==0 else odd[length//2]
 out.append(str(value))
print(' '.join(out))
