import sys
v=sys.stdin.read().split();out=[]
for s in v[1:1+int(v[0])]:
 edges=[{}];link=[-1];length=[0];last=0
 for c in s:
  current=len(edges);edges.append({});length.append(length[last]+1);link.append(0);p=last
  while p>=0 and c not in edges[p]:edges[p][c]=current;p=link[p]
  if p>=0:
   q=edges[p][c]
   if length[p]+1==length[q]:link[current]=q
   else:
    clone=len(edges);edges.append(edges[q].copy());length.append(length[p]+1);link.append(link[q])
    while p>=0 and edges[p].get(c)==q:edges[p][c]=clone;p=link[p]
    link[q]=link[current]=clone
  last=current
 out.append(str(sum(length[i]-length[link[i]] for i in range(1,len(edges)))))
print('\n'.join(out))
