import sys
v=sys.stdin.read().split();pattern=v[0];n=int(v[1]);matched=[s for s in v[2:2+n] if all(a=='*' or a==b for a,b in zip(pattern,s))]
print(len(matched))
if matched:print('\n'.join(matched))
