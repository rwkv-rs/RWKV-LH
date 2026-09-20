import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];a=v[2:2+n];b=iter(sorted(v[2+n:],reverse=True));a=[next(b) if x==0 else x for x in a];print('Yes' if any(a[i]>a[i+1] for i in range(n-1)) else 'No')
