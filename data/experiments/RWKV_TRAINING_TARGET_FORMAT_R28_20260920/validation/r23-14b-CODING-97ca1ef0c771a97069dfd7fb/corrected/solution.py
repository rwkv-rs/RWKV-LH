import sys
v=list(map(int,sys.stdin.read().split()));qs=v[1:1+v[0]];n=max(qs,default=0);ways=[0]*(n+1);ways[0]=1
for i in range(1,22):
 c=i**3
 for x in range(c,n+1):ways[x]+=ways[x-c]
print('\n'.join(str(ways[x]) for x in qs))
