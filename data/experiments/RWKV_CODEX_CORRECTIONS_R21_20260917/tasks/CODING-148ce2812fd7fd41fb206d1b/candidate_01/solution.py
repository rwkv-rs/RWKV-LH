import sys,math
n,m=map(int,sys.stdin.buffer.read().split());print(math.comb(n+2*m-1,2*m)%1000000007)
