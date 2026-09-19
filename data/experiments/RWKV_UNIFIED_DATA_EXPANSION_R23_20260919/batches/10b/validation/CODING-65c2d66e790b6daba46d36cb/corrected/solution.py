import sys
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i in range(v[0]):
 n,r=v[1+2*i:3+2*i];k=min(r,n-1);out.append(str(k*(k+1)//2+int(r>=n)))
print('\n'.join(out))
