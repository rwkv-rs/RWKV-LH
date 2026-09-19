import sys
v=iter(map(int,sys.stdin.read().split()));out=[];case=0
while True:
 try:n=next(v);m=next(v);t=next(v)
 except StopIteration:break
 if n==m==t==0:break
 parent=list(range(n));degree=[0]*n
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 for _ in range(m):
  a=next(v)-1;b=next(v)-1;degree[a]+=1;degree[b]+=1;parent[find(a)]=find(b)
 odd={}
 for i,d in enumerate(degree):
  if d:root=find(i);odd[root]=odd.get(root,0)+d%2
 trails=sum(max(1,count//2) for count in odd.values());case+=1;out.append(f'Case {case}: {(m+max(0,trails-1))*t}')
print('\n'.join(out))
