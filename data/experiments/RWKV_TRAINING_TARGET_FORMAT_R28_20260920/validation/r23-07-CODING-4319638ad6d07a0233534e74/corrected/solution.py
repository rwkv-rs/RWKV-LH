import sys
from collections import Counter
v=sys.stdin.buffer.read().split();at=0;out=[]
while at<len(v):
 n=int(v[at]);m=int(v[at+1]);at+=2
 if n==m==0:break
 counts=Counter(Counter(v[at:at+n]).values());at+=n;out.extend(str(counts[i]) for i in range(1,n+1))
print('\n'.join(out))
