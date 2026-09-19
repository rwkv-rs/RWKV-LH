import sys
f=sys.stdin.buffer;n,m=map(int,f.readline().split());a=list(range(1,n+1));rev=False;changed=[]
for line in f:
 p=list(map(int,line.split()))
 if not p:continue
 op=p[0]
 if op in (1,2):
  for j in changed:a[j]=j+1
  changed.clear();rev=op==2
 elif op==4:rev=not rev
 else:
  x,y=p[1]-1,p[2]-1
  if rev:x=n-1-x;y=n-1-y
  a[x],a[y]=a[y],a[x];changed.extend((x,y))
if rev:a.reverse()
print(*a)
