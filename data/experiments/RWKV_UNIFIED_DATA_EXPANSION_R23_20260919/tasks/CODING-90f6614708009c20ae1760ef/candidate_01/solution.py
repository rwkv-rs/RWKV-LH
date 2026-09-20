import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];parent=list(range(n));degree=[0]*n;components=n

def find(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
for a,b in zip(v[2::2],v[3::2]):
 a-=1;b-=1;degree[a]+=1;degree[b]+=1;aa=find(a);bb=find(b)
 if aa!=bb:parent[aa]=bb;components-=1
if any(d>2 for d in degree):print('NO');raise SystemExit
sizes={};ends={}
for i in range(n):
 root=find(i);sizes[root]=sizes.get(root,0)+1;ends[root]=ends.get(root,0)+2-degree[i]
if components>1 and any(ends[root]==0 for root in sizes):print('NO');raise SystemExit
added=[]
while len(added)<n-m:
 found=False
 for a in range(n):
  if degree[a]>=2:continue
  for b in range(a,n):
   if degree[b]>=2 or (a==b and degree[a]>0):continue
   aa=find(a);bb=find(b)
   if aa==bb and components>1:continue
   degree[a]+=1;degree[b]+=1;added.append((a+1,b+1))
   if aa!=bb:parent[aa]=bb;components-=1
   found=True;break
  if found:break
 if not found:print('NO');raise SystemExit
added.sort();print('YES');print(len(added))
for a,b in added:print(a,b)
