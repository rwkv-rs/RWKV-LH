import sys
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);p=next(v);rows=[{} for _ in range(n)]
for _ in range(p):
 i=next(v)-1;j=next(v);rows[i][j]=rows[i].get(j,0)+1
out=[]
for row in rows:
 bad=any(j<m and c>1+row.get(j+1,0) for j,c in row.items())
 out.append(str(-1 if bad else m-1+row.get(m,0)-row.get(1,0)))
print('\n'.join(out))
