import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);c=next(v);a=[next(v) for i in range(n)];votes=a.copy();votes[0]+=c;winner=max(range(n),key=lambda i:votes[i]);maximum=max(a);prefix=c;answer=[]
 for i,x in enumerate(a):
  prefix+=x;answer.append(0 if i==winner else i if prefix>=maximum else i+1)
 out.append(' '.join(map(str,answer)))
print('\n'.join(out))
