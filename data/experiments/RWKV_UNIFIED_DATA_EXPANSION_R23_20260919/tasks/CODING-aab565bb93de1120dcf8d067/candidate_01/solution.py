import sys
v=list(map(int,sys.stdin.read().split()));print('\n'.join(str(pow(v[i],v[i+1],v[i+2])) for i in range(0,len(v),3)))
