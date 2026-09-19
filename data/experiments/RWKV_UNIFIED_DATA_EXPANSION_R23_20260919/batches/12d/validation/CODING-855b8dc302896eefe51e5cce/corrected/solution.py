import sys
v=list(map(int,sys.stdin.buffer.read().split()));at=0;case=0;out=[]
while at<len(v):
 target=v[at];at+=1;g=[set() for _ in range(21)]
 while True:
  a,b=v[at:at+2];at+=2
  if a==b==0:break
  g[a].add(b);g[b].add(a)
 reachable={target};todo=[target]
 for x in todo:
  for y in g[x]:
   if y not in reachable:reachable.add(y);todo.append(y)
 case+=1;out.append('CASE '+str(case)+':');count=[0]
 def visit(x,path,seen):
  if x==target:out.append(' '.join(map(str,path)));count[0]+=1;return
  for y in sorted(g[x]):
   if y in reachable and not(seen>>y&1):visit(y,path+[y],seen|1<<y)
 if 1 in reachable:visit(1,[1],1<<1)
 out.append('There are '+str(count[0])+' routes from the firestation to streetcorner '+str(target)+'.')
print('\n'.join(out))
