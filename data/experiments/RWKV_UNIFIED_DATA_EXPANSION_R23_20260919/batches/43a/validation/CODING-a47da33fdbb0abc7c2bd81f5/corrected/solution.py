import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];a=sorted(v[2:],reverse=True);print(sum(c*(n-2*i-1) for i,c in enumerate(a[:min(k,n//2)])))
