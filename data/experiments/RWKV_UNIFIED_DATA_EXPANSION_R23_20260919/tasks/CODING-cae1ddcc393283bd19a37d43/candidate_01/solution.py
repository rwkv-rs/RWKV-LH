import sys
v=list(map(int,sys.stdin.read().split()));out=[]
for k in v[1:1+v[0]]:
 if k==0:out.append('a');continue
 first=(k-1)%25+1;blocks=(k-1)//25
 out.append(''.join(chr(97+i) for i in range(first,-1,-1))+'zyxwvutsrqponmlkjihgfedcba'*blocks)
print('\n'.join(out))
