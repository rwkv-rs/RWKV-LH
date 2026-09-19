import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for g,b in zip(v,v):
 if g<0 and b<0:break
 large=max(g,b);small=min(g,b);out.append(str((large+small)//(small+1)))
print('\n'.join(out))
