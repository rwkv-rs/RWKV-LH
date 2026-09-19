import sys
n=int(sys.stdin.buffer.read());s={0}
for _ in range(min(n,12)):
 s={x+d for x in s for d in (1,5,10,50)}
print(len(s)+max(0,n-12)*49)
