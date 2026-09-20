import sys
v=sys.stdin.buffer.read().split();s=v[1];trans=[{}];length=[0];link=[-1];occ=[0];last=0
for ch in s:
 cur=len(trans);trans.append({});length.append(length[last]+1);link.append(0);occ.append(1);p=last
 while p>=0 and ch not in trans[p]:trans[p][ch]=cur;p=link[p]
 if p>=0:
  q=trans[p][ch]
  if length[p]+1==length[q]:link[cur]=q
  else:
   clone=len(trans);trans.append(trans[q].copy());length.append(length[p]+1);link.append(link[q]);occ.append(0)
   while p>=0 and trans[p].get(ch)==q:trans[p][ch]=clone;p=link[p]
   link[q]=link[cur]=clone
 last=cur
counts=[0]*(len(s)+1)
for x in length:counts[x]+=1
for i in range(1,len(counts)):counts[i]+=counts[i-1]
order=[0]*len(trans)
for i,l in enumerate(length):counts[l]-=1;order[counts[l]]=i
answer=0
for u in reversed(order[1:]):
 if occ[u]>=2:answer=max(answer,length[u])
 occ[link[u]]+=occ[u]
print(answer)
