import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:];mean=sum(a)//n;p=0;s=[]
for x in a:p+=x-mean;s.append(p)
s.sort();median=s[n//2];print(sum(abs(x-median) for x in s))
