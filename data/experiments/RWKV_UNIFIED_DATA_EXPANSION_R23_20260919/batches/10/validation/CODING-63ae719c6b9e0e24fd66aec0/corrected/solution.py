import sys
out=[];closing={')':'(',']':'[','}':'{','>':'<','*)':'(*'};opening=set(closing.values())
for line in sys.stdin.read().splitlines():
 stack=[];i=0;position=0;failure=None
 while i<len(line):
  token=line[i:i+2] if line[i:i+2] in ('(*','*)') else line[i];i+=len(token);position+=1
  if token in opening:stack.append(token)
  elif token in closing:
   if not stack or stack.pop()!=closing[token]:failure=position;break
 if failure is None and stack:failure=position+1
 out.append('YES' if failure is None else 'NO '+str(failure))
print('\n'.join(out))
