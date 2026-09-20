import sys
v=sys.stdin.buffer.read().split();expression=v[0].decode();p,m=map(int,v[1:]);limit=min(p,m);minor='+' if p<=m else '-';stack=[];inf=10**12
for c in expression:
 if c.isdigit():value=int(c);stack.append(([value],[value],0))
 elif c==')':
  blo,bhi,bs=stack.pop();alo,ahi,asz=stack.pop();size=asz+bs+1;length=min(limit,size)+1;lo=[inf]*length;hi=[-inf]*length
  for i in range(len(alo)):
   if alo[i]==inf:continue
   for j in range(min(len(blo),length-i)):
    if blo[j]==inf:continue
    k=i+j+int(minor=='+')
    if k<length:lo[k]=min(lo[k],alo[i]+blo[j]);hi[k]=max(hi[k],ahi[i]+bhi[j])
    k=i+j+int(minor=='-')
    if k<length:lo[k]=min(lo[k],alo[i]-bhi[j]);hi[k]=max(hi[k],ahi[i]-blo[j])
  stack.append((lo,hi,size))
print(stack[0][1][limit])
