import sys
classes={'5':'2','9':'6'};out=[]
def kind(c):return classes.get(c,c)
for token in sys.stdin.read().split():
 if token=='.':break
 digits=token.replace('.','');counts={};answer=None
 for i in range(len(digits)-1,-1,-1):
  c=kind(digits[i]);counts[c]=counts.get(c,0)+1
  for x in range(int(digits[i])+1,10):
   k=kind(str(x))
   if counts.get(k,0):
    counts[k]-=1;suffix=''.join(c*counts[c] for c in sorted(counts));s=digits[:i]+str(x)+suffix;answer=s[:-1]+'.'+s[-1];break
  if answer is not None:break
 out.append(answer if answer else 'The price cannot be raised.')
print('\n'.join(out))
