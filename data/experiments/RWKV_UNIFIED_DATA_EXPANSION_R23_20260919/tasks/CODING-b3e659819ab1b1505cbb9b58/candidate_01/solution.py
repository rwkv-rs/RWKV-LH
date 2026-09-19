import sys
s,k=sys.stdin.read().split();k=int(k)
print('impossible' if len(s)<k else max(0,k-len(set(s))))
