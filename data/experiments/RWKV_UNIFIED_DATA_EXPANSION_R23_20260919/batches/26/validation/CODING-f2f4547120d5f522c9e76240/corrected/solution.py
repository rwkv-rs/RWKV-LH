import sys
sys.setrecursionlimit(100000)
lines=sys.stdin.read().splitlines();out=[]
for raw in lines[1:1+int(lines[0])]:
 s=raw;p=0
 def spaces():
  global p
  while p<len(s) and s[p].isspace():p+=1
 def atom():
  global p
  spaces()
  if p<len(s) and s[p]=='(':
   p+=1;value=expression();spaces()
   if p>=len(s) or s[p]!=')':raise ValueError
   p+=1;return value
  start=p
  while p<len(s) and '0'<=s[p]<='9':p+=1
  if p==start:raise ValueError
  return int(s[start:p])
 def product():
  global p
  value=atom();spaces()
  while p<len(s) and s[p]=='*':p+=1;value*=atom();spaces()
  return value
 def expression():
  global p
  value=product();spaces()
  while p<len(s) and s[p]=='+':p+=1;value+=product();spaces()
  return value
 try:
  value=expression();spaces()
  if p!=len(s):raise ValueError
  out.append(str(value))
 except (ValueError,RecursionError):out.append('ERROR')
print('\n'.join(out))
