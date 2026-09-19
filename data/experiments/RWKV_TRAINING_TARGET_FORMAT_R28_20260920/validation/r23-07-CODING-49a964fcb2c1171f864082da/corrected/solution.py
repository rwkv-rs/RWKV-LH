import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];rows=[]
for i in range(n):
 bits=0
 for j in range(n):bits|=v[1+i*n+j]<<j
 rows.append(bits)
for k in range(n):
 bit=1<<k;reachable=rows[k]
 for i in range(n):
  if rows[i]&bit:rows[i]|=reachable
print('\n'.join(' '.join(str((row>>j)&1) for j in range(n)) for row in rows))
