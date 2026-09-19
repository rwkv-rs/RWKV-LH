import sys
k=int(sys.stdin.buffer.read());width=(k-1).bit_length()
for x in range(k):print(''.join('Aa' if x>>j&1 else 'BB' for j in range(width)))
