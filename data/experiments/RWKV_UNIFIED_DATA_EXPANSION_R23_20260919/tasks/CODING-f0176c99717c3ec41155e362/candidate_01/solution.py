import sys,itertools
s=list(sys.stdin.read().strip());holes=[i for i,c in enumerate(s) if c=='.'];answer=-1
class Invalid(Exception):pass
def bounded(v):
 if not 0<=v<=1024:raise Invalid
 return v
def evaluate():
 p=0
 def atom():
  nonlocal p
  if p==len(s):raise Invalid
  if s[p]=='(':
   p+=1;v,ops=expression()
   if p==len(s) or s[p]!=')' or not ops:raise Invalid
   p+=1;return v
  if s[p] not in '01':raise Invalid
  value=0
  while p<len(s) and s[p] in '01':value=bounded(value*2+int(s[p]));p+=1
  return value
 def term():
  nonlocal p
  value=atom();ops=0
  while p<len(s) and s[p]=='*':p+=1;value=bounded(value*atom());ops+=1
  return value,ops
 def expression():
  nonlocal p
  value,ops=term()
  while p<len(s) and s[p] in '+-':
   op=s[p];p+=1;other,count=term();value=bounded(value+other if op=='+' else value-other);ops+=1+count
  return value,ops
 value,_=expression()
 if p!=len(s):raise Invalid
 return value
for chars in itertools.product('01+-*()',repeat=len(holes)):
 for i,c in zip(holes,chars):s[i]=c
 try:answer=max(answer,evaluate())
 except Invalid:pass
print(answer)
