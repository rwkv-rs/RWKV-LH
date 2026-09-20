import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=0;out=[]
while p<len(v):
 n=v[p];p+=1
 if not n:break
 d=[v[p+i*n:p+(i+1)*n] for i in range(n)];p+=n*n
 parent=[-1]*n;depth=[0]*n;degree=[0]*n
 def attach(root,leaf,length):
  for step in range(length):
   if step==length-1:w=leaf
   else:w=len(parent);parent.append(-1);depth.append(0);degree.append(0)
   parent[w]=root;depth[w]=depth[root]+1;degree[root]+=1;degree[w]+=1;root=w
 if n>1:attach(0,1,d[0][1])
 for j in range(2,n):
  t,i=max(((d[0][j]+d[0][i]-d[i][j])//2,i) for i in range(j))
  while depth[i]>t:i=parent[i]
  attach(i,j,d[0][j]-t)
 out.append(' '.join(map(str,sorted(x for x in degree if x>1))))
print('\n'.join(out))
