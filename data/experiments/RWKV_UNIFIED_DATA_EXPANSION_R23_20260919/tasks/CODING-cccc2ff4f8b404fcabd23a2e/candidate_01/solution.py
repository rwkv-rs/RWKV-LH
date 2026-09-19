import sys,math
out=[]
for s in sys.stdin.read().split():
 if s=='*':break
 value=1
 for i,c in enumerate(s,1):
  if c=='Y':value=math.lcm(value,i)
 out.append(str(value if all(c!='N' or value%i for i,c in enumerate(s,1)) else -1))
print('\n'.join(out))
