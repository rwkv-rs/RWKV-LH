import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];a=v[1::2];b=v[2::2];answer=[bytearray(b'0'*n),bytearray(b'0'*n)]
for row in answer:row[:n//2]=b'1'*(n//2)
combined=sorted([(x,0,i) for i,x in enumerate(a)]+[(x,1,i) for i,x in enumerate(b)])
for x,t,i in combined[:n]:answer[t][i]=49
print(answer[0].decode());print(answer[1].decode())
