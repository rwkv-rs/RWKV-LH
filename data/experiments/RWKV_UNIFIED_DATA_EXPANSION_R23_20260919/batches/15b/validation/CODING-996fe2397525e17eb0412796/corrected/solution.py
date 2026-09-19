import sys
v=iter(sys.stdin.read().split());out=[]
for _ in range(int(next(v))):
 n=int(next(v));x=int(next(v));s=next(v);balance=0;prefix=[]
 for c in s:prefix.append(balance);balance+=1 if c=='0' else -1
 if balance==0:answer=-1 if x in prefix else 0
 else:answer=sum((x-p)%balance==0 and (x-p)//balance>=0 for p in prefix)
 out.append(str(answer))
print('\n'.join(out))
