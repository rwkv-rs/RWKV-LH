import sys,bisect
lines=sys.stdin.buffer.read().splitlines();ops=[];students=[None]
for line in lines[1:]:
 v=line.split()
 if not v:continue
 if v[0]==b'D':A,B=map(int,v[1:]);students.append((B,A));ops.append((0,len(students)-1))
 else:ops.append((1,int(v[1])))
ordered=sorted(students[1:]);index={p:i for i,p in enumerate(ordered)};size=1
while size<len(ordered):size*=2
maximum=[-1]*(size*2);ids=[0]*len(ordered)
def activate(i,A,ident):
 ids[i]=ident;p=size+i;maximum[p]=A;p//=2
 while p:maximum[p]=max(maximum[p*2],maximum[p*2+1]);p//=2
def find(p,l,r,start,threshold):
 if r<start or maximum[p]<threshold:return -1
 if l==r:return l
 mid=(l+r)//2;answer=find(p*2,l,mid,start,threshold)
 return answer if answer>=0 else find(p*2+1,mid+1,r,start,threshold)
out=[]
for kind,ident in ops:
 B,A=students[ident];i=index[B,A]
 if kind==0:activate(i,A,ident)
 else:
  j=find(1,0,size-1,i+1,A);out.append(str(ids[j]) if j>=0 else 'NE')
print('\n'.join(out))
