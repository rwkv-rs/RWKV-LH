import sys
v=list(map(int,sys.stdin.buffer.read().split()));edges=[{}];link=[-1];length=[0];last=0;total=0;out=[]
for c in v[1:1+v[0]]:
 current=len(edges);edges.append({});link.append(0);length.append(length[last]+1);p=last
 while p>=0 and c not in edges[p]:edges[p][c]=current;p=link[p]
 if p>=0:
  q=edges[p][c]
  if length[p]+1==length[q]:link[current]=q
  else:
   clone=len(edges);edges.append(edges[q].copy());link.append(link[q]);length.append(length[p]+1)
   while p>=0 and edges[p].get(c)==q:edges[p][c]=clone;p=link[p]
   link[q]=link[current]=clone
 last=current;total+=length[current]-length[link[current]];out.append(str(total))
print('\n'.join(out))
