import sys
from itertools import groupby
v=sys.stdin.read().split();n=int(v[0]);runs=[len(list(g)) for c,g in groupby(v[1])];bad=sum(runs[i]+runs[i+1]-1 for i in range(len(runs)-1));print(n*(n-1)//2-bad)
