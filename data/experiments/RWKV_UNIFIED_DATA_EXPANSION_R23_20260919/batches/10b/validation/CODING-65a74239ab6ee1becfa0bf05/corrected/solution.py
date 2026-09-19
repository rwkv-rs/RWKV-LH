import sys
n=int(sys.stdin.read());print(-1 if n&1 else ' '.join(str(1<<i) for i in range(n.bit_length()-1,0,-1) if n>>i&1))
