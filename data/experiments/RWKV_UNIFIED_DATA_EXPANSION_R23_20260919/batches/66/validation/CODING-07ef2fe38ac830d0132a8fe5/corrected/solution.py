import sys
a,b=map(int,sys.stdin.buffer.read().split());n=a+b;k=2;answer=0
while k<=n:
 q=n//k;end=n//q;al=(a+q)//(q+1);bl=(b+q)//(q+1);ah=a//q;bh=b//q
 if al<=ah and bl<=bh:answer+=max(0,min(end,ah+bh)-max(k,al+bl)+1)
 k=end+1
print(answer)
