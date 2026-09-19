import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);children=[[] for _ in range(n)];at=1
for x in range(1,n):children[int(v[at])-1].append(x);at+=1
values=list(map(int,v[at:at+n]));at+=n;tin=[0]*n;tout=[0]*n;order=[];stack=[(0,False)]
while stack:
 x,done=stack.pop()
 if done:tout[x]=len(order)-1;continue
 tin[x]=len(order);order.append(x);stack.append((x,True));stack.extend((y,False) for y in reversed(children[x]))
tree=[0]*(4*n);lazy=[False]*(4*n)
def build(p,l,r):
 if l==r:tree[p]=values[order[l]];return
 mid=(l+r)//2;build(p*2,l,mid);build(p*2+1,mid+1,r);tree[p]=tree[p*2]+tree[p*2+1]
def flip(p,length):tree[p]=length-tree[p];lazy[p]=not lazy[p]
def query(p,l,r,a,b,change):
 if a<=l and r<=b:
  if change:flip(p,r-l+1)
  return tree[p]
 mid=(l+r)//2
 if lazy[p]:flip(p*2,mid-l+1);flip(p*2+1,r-mid);lazy[p]=False
 answer=0
 if a<=mid:answer+=query(p*2,l,mid,a,b,change)
 if b>mid:answer+=query(p*2+1,mid+1,r,a,b,change)
 if change:tree[p]=tree[p*2]+tree[p*2+1]
 return answer
build(1,0,n-1);q=int(v[at]);at+=1;out=[]
for _ in range(q):
 kind=v[at];x=int(v[at+1])-1;at+=2;answer=query(1,0,n-1,tin[x],tout[x],kind==b'pow')
 if kind==b'get':out.append(str(answer))
print('\n'.join(out))
