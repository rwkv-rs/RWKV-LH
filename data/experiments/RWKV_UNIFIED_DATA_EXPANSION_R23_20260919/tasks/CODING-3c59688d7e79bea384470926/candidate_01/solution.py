import sys,math
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
def count(a):
 if len(a)<2:return 1
 root=a[0];left=[x for x in a[1:] if x<root];right=[x for x in a[1:] if x>root]
 return math.comb(len(a)-1,len(left))*count(left)*count(right)
for _ in range(next(it)):
 n=next(it);out.append(str(count([next(it) for _ in range(n)])))
print('\n'.join(out))
