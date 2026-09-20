import sys
from collections import Counter
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];freq=Counter(a)
if max(freq.values())>(n+1)//2:print(-1)
else:
 bad=Counter(a[i] for i in range(n-1) if a[i]==a[i+1]);total=sum(bad.values());print(max((total+1)//2,max(bad.values(),default=0)))
