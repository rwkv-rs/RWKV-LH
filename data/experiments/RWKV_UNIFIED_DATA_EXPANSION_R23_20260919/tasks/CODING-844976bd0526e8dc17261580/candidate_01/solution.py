import sys,math
from collections import Counter
out=[]
for line in sys.stdin.read().splitlines():
 counts=Counter(c.lower() for c in line if 'a'<=c<='z' or 'A'<=c<='Z')
 if sum(x%2 for x in counts.values())>1:out.append('0');continue
 half=[x//2 for x in counts.values()];answer=math.factorial(sum(half))
 for count in half:answer//=math.factorial(count)
 out.append(str(answer))
print('\n'.join(out))
