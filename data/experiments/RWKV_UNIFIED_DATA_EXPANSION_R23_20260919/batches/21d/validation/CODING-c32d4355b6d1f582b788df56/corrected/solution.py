import sys
v=iter(map(int,sys.stdin.read().split()));n=next(v);m=next(v);count=[0]*n;nearest=[n]*n
for _ in range(m):
 a=next(v)-1;b=next(v)-1;count[a]+=1;nearest[a]=min(nearest[a],(b-a)%n)
print(' '.join(str(max((j-start)%n+(count[j]-1)*n+nearest[j] for j in range(n) if count[j])) for start in range(n)))
