import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);qwq=next(it);a=[next(it) for _ in range(n)];depth=(n-1).bit_length();scale=1<<depth;weights=[0]*n;stack=[(0,n-1,0)]
while stack:
 l,r,d=stack.pop()
 if l==r:weights[l]=2*scale-(scale>>d)
 else:mid=(l+r)//2;stack.append((mid+1,r,d+1));stack.append((l,mid,d+1))
prefix=[0];total=0
for x,w in zip(a,weights):prefix.append(prefix[-1]+w);total+=x*w
out=[]
for _ in range(m):
 l=next(it);r=next(it);x=next(it);total+=x*(prefix[r]-prefix[l-1]);out.append(str(total*qwq//scale))
print('\n'.join(out))
