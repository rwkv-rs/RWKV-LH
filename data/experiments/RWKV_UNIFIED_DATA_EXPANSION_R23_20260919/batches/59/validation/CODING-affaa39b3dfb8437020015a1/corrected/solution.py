import sys
k=int(sys.stdin.buffer.read());ways=[[1]];weights=[];L=0
while ways[-1][0]<=k:
 w=L^(L-1) if L else 0;weights.append(w);old=ways[-1];size=1
 while size<=max(w,len(old)-1):size*=2
 new=[0]*size
 for value,number in enumerate(old):new[value]+=number;new[value^w]+=number
 ways.append(new);L+=1
answer=checksum=0
for pos in range(L-1,-1,-1):
 zero=ways[pos][checksum] if checksum<len(ways[pos]) else 0
 if k>=zero:k-=zero;answer|=1<<pos;checksum^=weights[pos]
print(answer)
