import sys,re
sys.setrecursionlimit(1000000)
def parse(text):
 tokens=re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[+*-]',text);out=[];ops=[];want_value=True
 for token in tokens:
  if token in ('+','-','*'):
   if want_value:token='u'+token
   priority=3 if token.startswith('u') else (2 if token=='*' else 1)
   while ops and not token.startswith('u') and (3 if ops[-1].startswith('u') else (2 if ops[-1]=='*' else 1))>=priority:out.append(('op',ops.pop()))
   ops.append(token);want_value=True
  else:out.append(('number',int(token)) if token.isdigit() else ('name',token));want_value=False
 while ops:out.append(('op',ops.pop()))
 return out
variables={};answers=[]
for raw in sys.stdin:
 line=raw.strip()
 if not line:continue
 if line=='RESET':variables.clear()
 elif line.startswith('PRINT '):
  cache={};active=set()
  def evaluate(name):
   if name in cache:return cache[name]
   if name not in variables or name in active:raise ValueError
   active.add(name);stack=[]
   for kind,item in variables[name]:
    if kind=='number':stack.append(item)
    elif kind=='name':stack.append(evaluate(item))
    elif item.startswith('u'):stack[-1]= -stack[-1] if item=='u-' else stack[-1]
    else:
     b=stack.pop();a=stack.pop();stack.append(a+b if item=='+' else a-b if item=='-' else a*b)
   active.remove(name);cache[name]=stack[0];return stack[0]
  try:answers.append(str(evaluate(line.split()[1])))
  except (ValueError,RecursionError):answers.append('UNDEF')
 else:
  name,expression=line.split(':=',1);variables[name.strip()]=parse(expression)
print('\n'.join(answers))
