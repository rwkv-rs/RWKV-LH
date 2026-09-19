import sys
a=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i in range(1,len(a),2):
 x,y=a[i:i+2];out.append(f"{max(0,x-y)} {y}")
print('\n'.join(out))
