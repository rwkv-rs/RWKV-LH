import sys,math
m,n=map(int,sys.stdin.buffer.read().split());print(2*sum(math.comb(m-1,i) for i in range(min(n,m-1)+1)))
