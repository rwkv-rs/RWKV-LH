import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1:n+1];w=v[n+1:];left=[w[i] for i in range(n) if a[i]];right=[w[i] for i in range(n) if not a[i]];print(min(left)+min(right) if left and right else 0)
