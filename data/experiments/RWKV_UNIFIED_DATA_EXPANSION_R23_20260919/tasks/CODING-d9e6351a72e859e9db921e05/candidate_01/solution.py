import sys
v=sys.stdin.buffer.read().split();s=v[0].decode();k=int(v[1]);trans=[{}];link=[-1];length=[0];occ=[0];last=0
for ch in s:
 cur=len(trans);trans.append({});link.append(0);length.append(length[last]+1);occ.append(1);p=last
 while p>=0 and ch not in trans[p]:trans[p][ch]=cur;p=link[p]
 if p>=0:
  q=trans[p][ch]
  if length[p]+1==length[q]:link[cur]=q
  else:
   clone=len(trans);trans.append(trans[q].copy());link.append(link[q]);length.append(length[p]+1);occ.append(0)
   while p>=0 and trans[p].get(ch)==q:trans[p][ch]=clone;p=link[p]
   link[q]=link[cur]=clone
 last=cur
order=sorted(range(len(trans)),key=length.__getitem__,reverse=True)
for u in order:
 if link[u]>=0:occ[link[u]]+=occ[u]
count=[0]*len(trans)
for u in order:count[u]=(occ[u] if u else 0)+sum(count[z] for z in trans[u].values())
if k>count[0]:print('No such line.')
else:
 u=0;answer=[]
 while True:
  for ch,z in sorted(trans[u].items()):
   if k>count[z]:k-=count[z]
   else:
    answer.append(ch);u=z;break
  if k<=occ[u]:break
  k-=occ[u]
 print(''.join(answer))
