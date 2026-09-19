import sys
v=list(map(int,sys.stdin.buffer.read().split()));cache={1:1};out=[]
def length(x):
 path=[]
 while x not in cache:path.append(x);x=3*x+1 if x%2 else x//2
 value=cache[x]
 for p in reversed(path):value+=1;cache[p]=value
 return value
for i in range(0,len(v),2):
 a,b=v[i:i+2];out.append(str(a)+' '+str(b)+' '+str(max(length(x) for x in range(min(a,b),max(a,b)+1))))
print('\n'.join(out))
