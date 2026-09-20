import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);length=[0];link=[-1];nexts=[{}];owner=[-1];valid=[0];last=0
for label,word in enumerate(v[1:]):
 for position,c in enumerate(word+b'{'):
  cur=len(length);length.append(length[last]+1);link.append(0);nexts.append({});owner.append(label if c!=123 else -1);valid.append(position+1 if c!=123 else 0);p=last
  while p>=0 and c not in nexts[p]:nexts[p][c]=cur;p=link[p]
  if p>=0:
   q=nexts[p][c]
   if length[p]+1==length[q]:link[cur]=q
   else:
    clone=len(length);length.append(length[p]+1);link.append(link[q]);nexts.append(nexts[q].copy());owner.append(-1);valid.append(0)
    while p>=0 and nexts[p].get(c)==q:nexts[p][c]=clone;p=link[p]
    link[q]=link[cur]=clone
  last=cur
order=sorted(range(1,len(length)),key=length.__getitem__,reverse=True);answer=[0]*n
for u in order:
 p=link[u]
 if owner[u]>=0:answer[owner[u]]+=max(0,min(length[u],valid[u])-length[p])
 if owner[u]!=-1:
  if owner[p]==-1:owner[p]=owner[u]
  elif owner[p]!=owner[u]:owner[p]=-2
 valid[p]=max(valid[p],valid[u])
print('\n'.join(map(str,answer)))
