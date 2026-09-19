import sys
from collections import Counter
lines=iter(sys.stdin.read().splitlines());words=set()
for line in lines:
 if line.strip()=='#':break
 words.update(line.split())
dictionary=[Counter(w) for w in words];out=[]
for line in lines:
 if line.strip()=='#':break
 available=Counter(''.join(line.split()));out.append(str(sum(all(available[c]>=k for c,k in word.items()) for word in dictionary)))
print('\n'.join(out))
