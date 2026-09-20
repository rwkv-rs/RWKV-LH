import sys
parts=[]
def generate(a):
 if len(a)==4:parts.append(tuple(a));return
 for x in range(max(a)+2):generate(a+[x])
generate([0]);index={a:i for i,a in enumerate(parts)};k=len(parts);merge=[0]*(k*k*4);answers=[0]*(k*4)
def root(p,x):
 while p[x]!=x:x=p[x]
 return x
def join(p,a,b):p[root(p,a)]=root(p,b)
for ia,a in enumerate(parts):
 for ib,b in enumerate(parts):
  for edges in range(4):
   p=list(range(8))
   for x in range(4):join(p,x,a[x]);join(p,4+x,4+b[x])
   for row in range(2):
    if edges>>row&1:join(p,2+row,4+row)
   labels={};state=[]
   for x in (0,1,6,7):
    z=root(p,x)
    if z not in labels:labels[z]=len(labels)
    state.append(labels[z])
   merge[(ia*k+ib)*4+edges]=index[tuple(state)]
 for extra in range(4):
  p=list(range(4))
  for x in range(4):join(p,x,a[x])
  if extra&1:join(p,0,1)
  if extra&2:join(p,2,3)
  answers[ia*4+extra]=sum((root(p,r)==root(p,2+s))<<(2*r+s) for r in range(2) for s in range(2))
lines=iter(sys.stdin.buffer);n=int(next(lines));size=1
while size<n:size*=2
state=[-1]*(2*size);outgoing=[0]*(2*size);closed=index[(0,1,0,1)];opened=index[(0,0,0,0)]
for i in range(n):state[size+i]=closed
def pull(i):
 a=state[i*2];b=state[i*2+1]
 if a<0:state[i]=b;outgoing[i]=outgoing[i*2+1]
 elif b<0:state[i]=a;outgoing[i]=outgoing[i*2]
 else:state[i]=merge[(a*k+b)*4+outgoing[i*2]];outgoing[i]=outgoing[i*2+1]
for i in range(size-1,0,-1):pull(i)
def query(l,r):
 l+=size;r+=size+1;a=-1;b=-1;ae=be=0
 while l<r:
  if l&1:
   a=state[l] if a<0 else merge[(a*k+state[l])*4+ae];ae=outgoing[l];l+=1
  if r&1:
   r-=1
   if b<0:b=state[r];be=outgoing[r]
   else:b=merge[(state[r]*k+b)*4+outgoing[r]]
  l//=2;r//=2
 if a<0:return b
 if b<0:return a
 return merge[(a*k+b)*4+ae]
result=[]
for line in lines:
 v=line.split()
 if not v:continue
 if v[0]==b'Exit':break
 r1,c1,r2,c2=map(int,v[1:]);r1-=1;r2-=1;c1-=1;c2-=1
 if c1>c2:c1,c2=c2,c1;r1,r2=r2,r1
 if v[0]==b'Ask':
  middle=query(c1,c2);left=parts[query(0,c1)];right=parts[query(c2,n-1)];extra=int(left[2]==left[3])+2*int(right[0]==right[1]);mask=answers[middle*4+extra];result.append('Y' if mask>>(2*r1+r2)&1 else 'N')
 else:
  pos=size+c1
  if c1==c2:state[pos]=opened if v[0]==b'Open' else closed
  elif v[0]==b'Open':outgoing[pos]|=1<<r1
  else:outgoing[pos]&=~(1<<r1)
  pos//=2
  while pos:pull(pos);pos//=2
print('\n'.join(result))
