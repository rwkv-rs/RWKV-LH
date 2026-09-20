import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];a=v[2:];maximum=[0]*(4*n+8);lazy=[0]*(4*n+8)
def add(node,l,r,x,y):
 if x<=l and r<=y:maximum[node]+=1;lazy[node]+=1;return
 mid=(l+r)//2
 if x<=mid:add(node*2,l,mid,x,y)
 if y>mid:add(node*2+1,mid+1,r,x,y)
 maximum[node]=lazy[node]+max(maximum[node*2],maximum[node*2+1])
def query(node,l,r,x,y):
 if x<=l and r<=y:return maximum[node]
 mid=(l+r)//2;best=0
 if x<=mid:best=query(node*2,l,mid,x,y)
 if y>mid:best=max(best,query(node*2+1,mid+1,r,x,y))
 return best+lazy[node]
stack=[];out=[]
for r,value in enumerate(a):
 while stack and a[stack[-1]]<value:stack.pop()
 left=stack[-1]+1 if stack else 0;add(1,0,n-1,left,r);stack.append(r)
 if r+1>=k:out.append(str(query(1,0,n-1,r-k+1,r)))
print(' '.join(out))
