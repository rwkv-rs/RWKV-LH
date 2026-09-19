import sys
from collections import Counter
f=sys.stdin;line=f.readline()
while line and not line.strip():line=f.readline()
t=int(line);blocks=[];current=[]
for line in f:
 line=line.rstrip('\r\n')
 if line=='':
  if current:blocks.append(current);current=[]
 else:current.append(line)
if current:blocks.append(current)
out=[]
for block in blocks[:t]:
 counts=Counter(block);total=len(block);lines=[]
 for word in sorted(counts):
  units=(counts[word]*2000000+total)//(2*total);lines.append(f'{word} {units//10000}.{units%10000:04d}')
 out.append('\n'.join(lines))
print('\n\n'.join(out))
