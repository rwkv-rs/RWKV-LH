import sys,hashlib
read=sys.stdin.buffer.readline;n,m,q=map(int,read().split());width=m+1;tree=[0]*((n+1)*width)
def update(x,y,value):
 while x<=n:
  base=x*width;j=y
  while j<=m:tree[base+j]^=value;j+=j&-j
  x+=x&-x
def query(x,y):
 result=0
 while x:
  base=x*width;j=y
  while j:result^=tree[base+j];j-=j&-j
  x-=x&-x
 return result
out=[]
for _ in range(q):
 kind,x,y,u,v=map(int,read().split())
 if kind==3:out.append('Yes' if query(x,y)==query(u,v) else 'No')
 else:
  value=int.from_bytes(hashlib.blake2b(f'{x},{y},{u},{v}'.encode(),digest_size=16).digest(),'little')
  update(x,y,value);update(u+1,y,value);update(x,v+1,value);update(u+1,v+1,value)
print('\n'.join(out))
