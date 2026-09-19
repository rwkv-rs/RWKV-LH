import sys
from collections import Counter
v=list(map(int,sys.stdin.read().split()));n=v[0];a=v[1:n+1];b=v[n+1:];counts=Counter(a);duplicated=[x for x,c in counts.items() if c>1];allowed={x:any(x&y==x for y in duplicated) for x in counts};print(sum(score for x,score in zip(a,b) if allowed[x]))
