import sys
v=list(map(int,sys.stdin.buffer.read().split()));heights=sorted(v[1:])[:-1];levels=sorted(set(heights));possible=1
for h in heights:
 following=0
 for level in levels:
  if level>=h:following|=possible<<(level-h)
 possible=following
print(' '.join(str(i) for i in range(possible.bit_length()) if possible>>i&1))
