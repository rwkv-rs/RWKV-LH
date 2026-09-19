import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 s=next(v);c=next(v);row=[next(v) for i in range(s)];last=[]
 while row:
  last.append(row[-1]);row=[row[i+1]-row[i] for i in range(len(row)-1)]
 continuation=[]
 for _ in range(c):
  for j in range(len(last)-2,-1,-1):last[j]+=last[j+1]
  continuation.append(str(last[0]))
 out.append(' '.join(continuation))
print('\n'.join(out))
