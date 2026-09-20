import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);graph=[[next(it)-1 for _ in range(next(it))] for u in range(n)];offset=[0]
for edges in graph:offset.append(offset[-1]+len(edges))
position=[{v:i for i,v in enumerate(edges)} for edges in graph];transitions=[];color=[]
for u,edges in enumerate(graph):
 targets=[offset[v]+position[v][u] for v in edges]
 for i in range(len(edges)):transitions.append(targets[i:]+targets[:i]);color.append(len(edges))
while True:
 classes={};new=[]
 for i,targets in enumerate(transitions):
  key=(color[i],tuple(color[j] for j in targets))
  if key not in classes:classes[key]=len(classes)
  new.append(classes[key])
 if len(set(new))==len(set(color)):color=new;break
 color=new
groups={}
for u in range(n):
 key=min(color[offset[u]:offset[u+1]],default=-1);groups.setdefault(key,[]).append(u+1)
result=[group for group in groups.values() if len(group)>1];result.sort(key=lambda a:a[0]);print('\n'.join(' '.join(map(str,a)) for a in result) if result else 'none')
