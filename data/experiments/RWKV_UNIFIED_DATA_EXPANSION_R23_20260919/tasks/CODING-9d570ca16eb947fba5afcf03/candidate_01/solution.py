import sys
v=iter(map(int,sys.stdin.read().split()));n=next(v);m=next(v);k=next(v);a=[[next(v) for _ in range(m)] for _ in range(n)]
if n<=k and m>k:a=list(map(list,zip(*a)));n,m=m,n
rows=[sum(x<<j for j,x in enumerate(row)) for row in a]
candidates=set(rows) if n>k else range(1<<m)
best=k+1
for mask in candidates:
 total=0
 for row in rows:
  d=(row^mask).bit_count();total+=min(d,m-d)
  if total>=best:break
 best=min(best,total)
print(best if best<=k else -1)
