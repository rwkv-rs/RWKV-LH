import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);groups={};answer=0
for text in v[1:n+1]:
 patterns=[];best=0
 for i,char in enumerate(text):
  key=(i,text[:i]+text[i+1:]);digit=char-48;patterns.append((key,digit));stored=groups.get(key)
  if stored is not None:best=max(best,stored[0]-digit,stored[1]+digit)
 for key,digit in patterns:
  old=groups.get(key)
  if old is None:groups[key]=(best+digit,best-digit)
  else:groups[key]=(max(old[0],best+digit),max(old[1],best-digit))
 answer=max(answer,best)
print(answer)
