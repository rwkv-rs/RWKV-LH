import sys
lines=iter(sys.stdin.read().splitlines());output=[]
for line in lines:
 if not line.strip():continue
 n,length=map(int,line.split())
 if n==length==0:break
 rules=[]
 for _ in range(n):
  line=next(lines).strip();lhs,rhs=line.split('=',1);rules.append((ord(lhs)-65,rhs))
 best=[[None]*(length+1) for _ in range(26)]
 for target in range(length+1):
  changed=True
  while changed:
   changed=False
   for lhs,rhs in rules:
    values=['']+[None]*target
    for char in rhs:
     following=[None]*(target+1)
     if char.islower():
      for used in range(target):
       if values[used] is not None:following[used+1]=values[used]+char
     else:
      options=best[ord(char)-65]
      for used,prefix in enumerate(values):
       if prefix is None:continue
       for size in range(target-used+1):
        suffix=options[size]
        if suffix is not None:
         value=prefix+suffix;old=following[used+size]
         if old is None or value<old:following[used+size]=value
     values=following
     if not any(value is not None for value in values):break
    value=values[target]
    if value is not None and (best[lhs][target] is None or value<best[lhs][target]):best[lhs][target]=value;changed=True
 answer=best[18][length];output.append('-' if answer is None else answer)
sys.stdout.write('\n'.join(output)+'\n')
