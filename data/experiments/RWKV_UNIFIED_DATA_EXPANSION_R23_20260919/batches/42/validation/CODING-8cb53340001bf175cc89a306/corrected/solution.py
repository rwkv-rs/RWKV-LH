import sys
v=sys.stdin.buffer.read().split();out=[];mod=1000000007
for i in range(int(v[0])):
 s,t=v[1+2*i:3+2*i];value=0
 for a,b in zip(s,t):value=(26*value+b-a)%mod
 out.append(f'Case {i+1}: {(value-1)%mod}')
print('\n'.join(out))
