import sys
v=list(map(int,sys.stdin.read().split()));n=v[0];a=v[1:];mean=sum(a)//n;prefix=[];balance=0
for x in a:balance+=x-mean;prefix.append(balance)
prefix.sort();median=prefix[n//2];print(sum(abs(x-median) for x in prefix))
