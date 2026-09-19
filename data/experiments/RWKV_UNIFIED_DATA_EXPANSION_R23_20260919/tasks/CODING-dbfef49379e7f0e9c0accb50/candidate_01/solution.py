import sys
lines=iter(sys.stdin.read().splitlines());t=int(next(lines));out=[]
for _ in range(t):
 recording=next(lines).split();known=set()
 for line in lines:
  if line=='what does the fox say?':break
  known.add(line.split(' goes ',1)[1])
 out.append(' '.join(sound for sound in recording if sound not in known))
print('\n'.join(out))
