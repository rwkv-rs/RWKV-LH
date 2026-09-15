n=int(input());depth=n.bit_length();x=1;turn=0
while x<=n:
    x=2*x+int((turn==0)==(depth%2==1));turn^=1
print('Takahashi' if turn==0 else 'Aoki')
