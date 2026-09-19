import sys
v=sys.stdin.buffer.read().split();at=0;out=[]
def sign(x):return (x>0)-(x<0)
while at<len(v):
 n=int(v[at]);q=int(v[at+1]);at+=2;size=1
 while size<n:size*=2
 tree=[1]*(2*size)
 for i in range(n):tree[size+i]=sign(int(v[at+i]))
 at+=n
 for i in range(size-1,0,-1):tree[i]=tree[2*i]*tree[2*i+1]
 answer=[]
 for _ in range(q):
  kind=v[at];left=int(v[at+1]);right=int(v[at+2]);at+=3
  if kind==b'C':
   p=size+left-1;tree[p]=sign(right);p//=2
   while p:tree[p]=tree[2*p]*tree[2*p+1];p//=2
  else:
   l=size+left-1;r=size+right;value=1
   while l<r:
    if l&1:value*=tree[l];l+=1
    if r&1:r-=1;value*=tree[r]
    l//=2;r//=2
   answer.append('+' if value>0 else '-' if value<0 else '0')
 out.append(''.join(answer))
print('\n'.join(out))
