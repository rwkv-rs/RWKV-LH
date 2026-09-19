import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=sorted(v[1:n+1]);p=[0]
for x in a:p.append(p[-1]+x)
out=[]
for i in range(v[n+1]):
 l,r=v[n+2+2*i:n+4+2*i];out.append(str(p[bisect.bisect_right(a,r)]-p[bisect.bisect_left(a,l)]) if l<=r else '0')
print('\n'.join(out))
