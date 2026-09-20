import sys
from collections import deque
sys.setrecursionlimit(10000)
ALL=(1<<26)-1

def compile_clue(text):
 pattern=text[1:-1];eps=[];letters=[];at=0
 def node():eps.append([]);return len(eps)-1
 def atom():
  nonlocal at
  ch=pattern[at];at+=1
  if ch=='(':
   a,b=alternate();assert pattern[at]==')';at+=1
  else:
   a=node();b=node();letters.append((a,ALL if ch=='.' else 1<<(ord(ch)-65),b))
  if at<len(pattern) and pattern[at]=='*':
   at+=1;u=node();v=node();eps[u].extend([a,v]);eps[b].extend([a,v]);a,b=u,v
  return a,b
 def concatenate():
  a,b=atom()
  while at<len(pattern) and pattern[at] not in '|)':
   c,d=atom();eps[b].append(c);b=d
  return a,b
 def alternate():
  nonlocal at
  a,b=concatenate()
  while at<len(pattern) and pattern[at]=='|':
   at+=1;c,d=concatenate();u=node();v=node();eps[u].extend([a,c]);eps[b].append(v);eps[d].append(v);a,b=u,v
  return a,b
 start,finish=alternate();reverse=[[] for _ in eps]
 for u,neighbors in enumerate(eps):
  for v in neighbors:reverse[v].append(u)
 def closure(graph,u):
  seen=1<<u;stack=[u]
  while stack:
   current=stack.pop()
   for v in graph[current]:
    bit=1<<v
    if not seen&bit:seen|=bit;stack.append(v)
  return seen
 begin=closure(eps,start);end=1<<finish;edges=[(1<<u,label,closure(eps,v),closure(reverse,u)) for u,label,v in letters]
 def supports(domains):
  forward=[begin]
  for domain in domains:
   active=forward[-1];following=0
   for source,label,destination,previous in edges:
    if source&active and label&domain:following|=destination
   if not following:return None
   forward.append(following)
  if not forward[-1]&end:return None
  backward=end;answer=[0]*len(domains)
  for i in range(len(domains)-1,-1,-1):
   previous_states=0;allowed=0;domain=domains[i]
   for source,label,destination,previous in edges:
    if destination&backward and label&domain:
     previous_states|=previous
     if source&forward[i]:allowed|=label&domain
   answer[i]=allowed;backward=previous_states
  return answer
 return supports
values=iter(sys.stdin.read().split());output=[]
for token in values:
 h=int(token);w=int(next(values))
 if h==w==0:break
 clues=[compile_clue(next(values)) for _ in range(h+w)];lines=[[r*w+c for c in range(w)] for r in range(h)]+[[r*w+c for r in range(h)] for c in range(w)];solutions=[]
 def search(domains,changed):
  queue=deque(changed);pending=set(changed)
  while queue:
   line=queue.popleft();pending.remove(line);cells=lines[line];support=clues[line]([domains[i] for i in cells])
   if support is None:return
   for cell,allowed in zip(cells,support):
    new=domains[cell]&allowed
    if not new:return
    if new!=domains[cell]:
     domains[cell]=new
     for affected in (cell//w,h+cell%w):
      if affected not in pending:pending.add(affected);queue.append(affected)
  choices=[i for i,d in enumerate(domains) if d&(d-1)]
  if not choices:
   solutions.append(''.join(chr(64+d.bit_length()) for d in domains));return
  cell=min(choices,key=lambda i:domains[i].bit_count());options=domains[cell]
  while options and len(solutions)<2:
   bit=options&-options;options-=bit;child=domains[:];child[cell]=bit;search(child,[cell//w,h+cell%w])
 search([ALL]*(h*w),range(h+w))
 if not solutions:output.append('none')
 elif len(solutions)>1:output.append('ambiguous')
 else:
  answer=solutions[0];output.extend(answer[r*w:(r+1)*w] for r in range(h))
print('\n'.join(output))
