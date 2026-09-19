import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for case in range(1,next(v)+1):
 n=next(v);q=next(v);a=[next(v) for i in range(n)];groups=[0]*n
 for i in range(1,n):groups[i]=groups[i-1]+(a[i]!=a[i-1])
 out.append(f'Case {case}:')
 for _ in range(q):
  left=next(v)-1;right=next(v)-1;out.append(str(groups[right]-groups[left]+1))
print('\n'.join(out))
