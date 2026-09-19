import sys
v=iter(sys.stdin.read().split());out=[]
for token in v:
 n=int(token);s=next(v);stack=[0];cuts=0;deepest=-1;answer=0
 for c in s:
  depth=stack.pop()
  if c=='1':cuts+=1;stack.extend((depth+1,depth+1))
  elif depth>deepest:deepest=depth;answer=cuts
 out.append(str(answer))
print('\n'.join(out))
