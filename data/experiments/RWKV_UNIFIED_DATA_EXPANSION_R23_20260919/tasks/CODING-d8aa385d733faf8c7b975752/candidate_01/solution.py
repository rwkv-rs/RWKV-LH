import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);values=[next(it) for _ in range(n)];graph=[[] for _ in range(n)]
for _ in range(n-1):
 a=next(it)-1;b=next(it)-1;graph[a].append(b);graph[b].append(a)
entry=[0]*n;end=[0]*n;initial=[0]*n;clock=0;stack=[(0,-1,False)]
while stack:
 u,parent,leave=stack.pop()
 if leave:end[u]=clock;continue
 entry[u]=clock;clock+=1;initial[u]=values[u]+(initial[parent] if parent>=0 else 0);stack.append((u,parent,True))
 for v in graph[u]:
  if v!=parent:stack.append((v,u,False))
bit=[0]*(n+2)
def add(i,delta):
 i+=1
 while i<=n:bit[i]+=delta;i+=i&-i
out=[]
for _ in range(next(it)):
 op=next(it);u=next(it)-1
 if op==1:
  i=entry[u]+1;value=initial[u]
  while i:value+=bit[i];i-=i&-i
  out.append(str(value))
 else:
  value=next(it);delta=value-values[u];values[u]=value;add(entry[u],delta);add(end[u],-delta)
print('\n'.join(out))
