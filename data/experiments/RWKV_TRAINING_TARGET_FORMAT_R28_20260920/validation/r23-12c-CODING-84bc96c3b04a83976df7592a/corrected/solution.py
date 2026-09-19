import sys
out=[]
for line in sys.stdin.read().splitlines():
 count=0;parts=[]
 for c in line:
  if '0'<=c<='9':count+=ord(c)-48
  elif c=='!':parts.append('\n')
  else:parts.append((' ' if c=='b' else c)*count);count=0
 out.append(''.join(parts))
sys.stdout.write('\n'.join(out)+'\n')
