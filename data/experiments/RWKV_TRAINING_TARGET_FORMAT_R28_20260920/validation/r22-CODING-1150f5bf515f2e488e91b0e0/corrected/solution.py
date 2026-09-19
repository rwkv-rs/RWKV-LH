import sys
s=sys.stdin.buffer.readline().strip();n=len(s);v=list(map(int,sys.stdin.buffer.read().split()));q=v[0];queries=sorted((v[2+2*i],v[1+2*i],i) for i in range(q));bit=[0]*(n+1);stack=[];answer=[0]*q;pos=0;total=0
for r,l,i in queries:
 while pos<r:
  if s[pos]==40:stack.append(pos+1)
  elif stack:
   x=stack.pop();total+=1
   while x<=n:bit[x]+=1;x+=x&-x
  pos+=1
 x=l-1;before=0
 while x:before+=bit[x];x-=x&-x
 answer[i]=2*(total-before)
print('\n'.join(map(str,answer)))
