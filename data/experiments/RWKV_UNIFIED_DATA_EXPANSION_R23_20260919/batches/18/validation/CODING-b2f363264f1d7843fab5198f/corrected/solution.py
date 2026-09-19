import sys
v=sys.stdin.read().split();out=[];weights={'x':2,'y':4,'z':10}
for s in v[1:1+int(v[0])]:
 stack=[0];i=0
 while i<len(s):
  c=s[i];i+=1
  if c=='(':stack.append(0);continue
  value=stack.pop() if c==')' else weights[c];j=i
  while i<len(s) and s[i].isdigit():i+=1
  multiplier=int(s[j:i]) if i>j else 1;stack[-1]+=value*multiplier
 out.append(str(stack[0]))
print('\n'.join(out))
