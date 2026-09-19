import sys
from array import array
a,b=sys.stdin.read().split();trans=[{}];link=[-1];length=[0];last=0
for ch in b:
 cur=len(trans);trans.append({});length.append(length[last]+1);link.append(0);p=last
 while p>=0 and ch not in trans[p]:trans[p][ch]=cur;p=link[p]
 if p>=0:
  q=trans[p][ch]
  if length[p]+1==length[q]:link[cur]=q
  else:
   clone=len(trans);trans.append(trans[q].copy());length.append(length[p]+1);link.append(link[q])
   while p>=0 and trans[p].get(ch)==q:trans[p][ch]=clone;p=link[p]
   link[q]=link[cur]=clone
 last=cur
inf=len(a)+1;answer1=inf;state=matched=0
for i,ch in enumerate(a):
 while state and ch not in trans[state]:state=link[state];matched=min(matched,length[state])
 if ch in trans[state]:state=trans[state][ch];matched+=1
 else:matched=0
 if matched<i+1:answer1=min(answer1,matched+1)
m=len(b);nxt=[None]*(m+1);nxt[m]=array('i',[-1])*26
for i in range(m-1,-1,-1):nxt[i]=nxt[i+1][:];nxt[i][ord(b[i])-97]=i+1
answer2=inf;codes=[ord(c)-97 for c in a]
for i in range(len(a)):
 pos=0
 for j in range(i,min(len(a),i+answer2)):
  pos=nxt[pos][codes[j]]
  if pos<0:answer2=min(answer2,j-i+1);break
def shortest(transitions,states):
 dp=[inf]*states;dp[0]=0;answer=inf
 for ch in a:
  updated=dp[:]
  for state,cost in enumerate(dp):
   if cost+1>=answer:continue
   to=transitions(state,ch)
   if to<0:answer=cost+1
   elif cost+1<updated[to]:updated[to]=cost+1
  dp=updated
 return answer
answers=[answer1,answer2,shortest(lambda s,c:trans[s].get(c,-1),len(trans)),shortest(lambda s,c:nxt[s][ord(c)-97],m+1)]
print('\n'.join(str(x if x<inf else -1) for x in answers))
