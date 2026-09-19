import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];x=sorted(v[1:n+1]);prefix=[0]
for value in x:prefix.append(prefix[-1]+value)
out=[]
for i in range(v[n+1]):
 a,b=v[n+2+2*i:n+4+2*i];index=(b*n-1)//(a+b);y=x[index];out.append(str(a*(y*index-prefix[index])+b*(prefix[n]-prefix[index+1]-y*(n-index-1))))
print('\n'.join(out))
