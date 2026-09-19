import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
while True:
 n=next(v);root=next(v)-1
 if n==0:break
 weight=[next(v) for _ in range(n)];size=[1]*n;parent=list(range(n));leader=list(range(n));alive=set(range(n));answer=sum(weight)
 for _ in range(n-1):a=next(v)-1;b=next(v)-1;parent[b]=a
 def find(x):
  while leader[x]!=x:leader[x]=leader[leader[x]];x=leader[x]
  return x
 for _ in range(n-1):
  chosen=-1
  for x in alive:
   if x!=root and (chosen<0 or weight[x]*size[chosen]>weight[chosen]*size[x]):chosen=x
  p=find(parent[chosen]);answer+=size[p]*weight[chosen];size[p]+=size[chosen];weight[p]+=weight[chosen];leader[chosen]=p;alive.remove(chosen)
 out.append(str(answer))
print('\n'.join(out))
