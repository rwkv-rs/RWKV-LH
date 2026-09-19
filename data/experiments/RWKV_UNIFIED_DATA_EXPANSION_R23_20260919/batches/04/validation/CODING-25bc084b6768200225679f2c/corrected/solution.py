import sys
v=sys.stdin.read().split();n=int(v[0]);distances=[row.index('S')-row.index('G') for row in v[2:2+n]]
print(-1 if any(x<0 for x in distances) else len(set(distances)))
